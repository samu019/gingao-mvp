from django.db import models

from assets_app.models import Asset

from .audio_providers import (
    get_audio_provider,
)


AUDIO_ASSET_SUFFIX = "Narracion"


def _field_names(model):
    return {
        field.name: field
        for field in model._meta.fields
    }


def _required_fields_satisfied(
    model,
    kwargs,
):
    supplied = set(
        kwargs.keys()
    )

    for field in model._meta.fields:

        if field.primary_key:
            continue

        if field.name in supplied:
            continue

        if field.auto_created:
            continue

        if getattr(
            field,
            "auto_now",
            False
        ):
            continue

        if getattr(
            field,
            "auto_now_add",
            False
        ):
            continue

        if field.has_default():
            continue

        if field.null:
            continue

        if field.blank:
            continue

        if isinstance(
            field,
            models.BooleanField
        ):
            continue

        return False, field.name

    return True, None


def project_narration_text(
    project
):
    parts = []

    for scene in (
        project.scenes
        .all()
        .order_by("position")
    ):

        script = (
            scene.script
            or ""
        ).strip()

        if script:
            parts.append(script)

    return "\n\n".join(parts)


def project_duration(
    project
):
    return sum(
        int(
            scene.duration_seconds
            or 0
        )
        for scene in (
            project.scenes
            .all()
        )
    )


def _asset_url(asset):

    if asset is None:
        return ""

    for field_name in [
        "url",
        "file_url",
        "source_url",
    ]:
        if hasattr(
            asset,
            field_name
        ):
            value = getattr(
                asset,
                field_name
            )

            if value:
                return value

    return ""


def _asset_name(
    project
):
    return (
        f"{project.title} - "
        f"{AUDIO_ASSET_SUFFIX}"
    )


def find_project_audio_asset(
    *,
    project,
    user,
):
    fields = _field_names(
        Asset
    )

    filters = {}

    name = _asset_name(
        project
    )

    if "owner" in fields:
        filters["owner"] = user

    elif "user" in fields:
        filters["user"] = user

    if "project" in fields:
        filters["project"] = project

    if "name" in fields:
        filters["name"] = name

    elif "title" in fields:
        filters["title"] = name

    if not filters:
        return None

    return (
        Asset.objects
        .filter(**filters)
        .order_by("-pk")
        .first()
    )


def create_audio_asset(
    *,
    project,
    user,
    url,
):
    fields = _field_names(
        Asset
    )

    name = _asset_name(
        project
    )

    candidates = {
        "owner": user,
        "user": user,
        "project": project,

        "name": name,
        "title": name,

        "kind": "audio",
        "asset_type": "audio",
        "type": "audio",

        "url": url,
        "file_url": url,
        "source_url": url,
    }

    kwargs = {}

    for key, value in (
        candidates.items()
    ):
        if key in fields:
            kwargs[key] = value

    ok, missing = (
        _required_fields_satisfied(
            Asset,
            kwargs,
        )
    )

    if not ok:
        return None, missing

    existing = (
        find_project_audio_asset(
            project=project,
            user=user,
        )
    )

    if existing:

        for key, value in (
            kwargs.items()
        ):
            setattr(
                existing,
                key,
                value,
            )

        existing.save()

        return existing, None

    return (
        Asset.objects.create(
            **kwargs
        ),
        None
    )


def generate_project_audio(
    *,
    project,
    user,
    provider_code=None,
):
    # GINGAO_VOICE_PIPELINE_V39A
    if not bool(
        getattr(
            project,
            "voice_enabled",
            True,
        )
    ):
        return {
            "url": "",
            "provider": None,
            "duration": 0,
            "external_cost_usd": 0.0,
            "is_mock": False,
            "asset": None,
            "asset_missing_field": None,
            "disabled": True,
        }

    provider = get_audio_provider(
        provider_code
    )

    text = project_narration_text(
        project
    )

    if not text:
        raise RuntimeError(
            "El proyecto no tiene "
            "texto para narrar."
        )

    duration = project_duration(
        project
    )

    result = provider.generate(
        text=text,
        project=project,
        duration_seconds=duration,
    )

    if not result.success:
        raise RuntimeError(
            result.error
            or "Error generando audio."
        )

    asset, missing = (
        create_audio_asset(
            project=project,
            user=user,
            url=result.url,
        )
    )

    return {
        "url": result.url,
        "provider":
            result.provider,
        "duration":
            result.duration_seconds,
        "external_cost_usd":
            result.external_cost_usd,
        "is_mock":
            result.is_mock,
        "asset":
            asset,
        "asset_missing_field":
            missing,
    }


def get_project_audio_info(
    *,
    project,
    user,
):
    if not bool(
        getattr(
            project,
            "voice_enabled",
            True,
        )
    ):
        return {
            "asset": None,
            "url": "",
            "disabled": True,
        }

    asset = (
        find_project_audio_asset(
            project=project,
            user=user,
        )
    )

    return {
        "asset": asset,
        "url": _asset_url(
            asset
        ),
    }
