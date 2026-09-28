from django.db import transaction
from django.db import models

from assets_app.models import Asset
from generations.models import VideoGeneration

from .video_providers import get_video_provider


def _field_names(model):
    return {
        field.name: field
        for field in model._meta.fields
    }


def _set_if_exists(
    kwargs,
    fields,
    name,
    value,
):
    if name in fields:
        kwargs[name] = value


def _video_generation_kwargs(
    *,
    user,
    project,
    scene,
    storyboard,
    provider,
    result,
):
    fields = _field_names(
        VideoGeneration
    )

    kwargs = {}

    candidates = {
        "owner": user,
        "user": user,
        "project": project,
        "scene": scene,
        "storyboard": storyboard,

        "provider": provider.code,
        "provider_code": provider.code,

        "status": "ready",
        "state": "ready",

        "prompt": scene.video_prompt,
        "video_prompt": scene.video_prompt,

        "output_url": result.url,
        "video_url": result.url,
        "url": result.url,
        "file_url": result.url,

        "cost_credits": provider.credit_cost,
        "credits_cost": provider.credit_cost,
        "credit_cost": provider.credit_cost,

        "external_cost_usd":
            result.external_cost_usd,

        "duration_seconds":
            scene.duration_seconds,

        "duration":
            scene.duration_seconds,
    }

    for key, value in candidates.items():
        _set_if_exists(
            kwargs,
            fields,
            key,
            value,
        )

    return kwargs


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

        # BooleanFields tienen default impl?cito
        if isinstance(
            field,
            models.BooleanField
        ):
            continue

        return False, field.name

    return True, None


def create_video_generation(
    *,
    user,
    project,
    scene,
    storyboard,
    provider,
    result,
):
    kwargs = _video_generation_kwargs(
        user=user,
        project=project,
        scene=scene,
        storyboard=storyboard,
        provider=provider,
        result=result,
    )

    ok, missing = (
        _required_fields_satisfied(
            VideoGeneration,
            kwargs,
        )
    )

    if not ok:
        return None, missing

    generation = None

    fields = _field_names(
        VideoGeneration
    )

    filters = {}

    if "scene" in fields:
        filters["scene"] = scene

    if (
        "project" in fields
        and not filters
    ):
        filters["project"] = project

    if filters:
        generation = (
            VideoGeneration.objects
            .filter(**filters)
            .order_by("-pk")
            .first()
        )

    if generation:

        for key, value in kwargs.items():
            setattr(
                generation,
                key,
                value,
            )

        generation.save()

        return generation, None

    return (
        VideoGeneration.objects.create(
            **kwargs
        ),
        None
    )


def _video_asset_kwargs(
    *,
    user,
    project,
    scene,
    url,
):
    fields = _field_names(
        Asset
    )

    name = (
        f"{project.title} - "
        f"Video escena {scene.position}"
    )

    values = {
        "owner": user,
        "user": user,
        "project": project,

        "name": name,
        "title": name,

        "kind": "video",
        "asset_type": "video",
        "type": "video",

        "url": url,
        "file_url": url,
        "source_url": url,
    }

    kwargs = {}

    for key, value in values.items():

        if key in fields:
            kwargs[key] = value

    return kwargs


def create_video_asset(
    *,
    user,
    project,
    scene,
    url,
):
    kwargs = _video_asset_kwargs(
        user=user,
        project=project,
        scene=scene,
        url=url,
    )

    ok, missing = (
        _required_fields_satisfied(
            Asset,
            kwargs,
        )
    )

    if not ok:
        return None, missing

    fields = _field_names(
        Asset
    )

    existing = None

    if (
        "owner" in fields
        and "name" in fields
    ):
        existing = Asset.objects.filter(
            owner=user,
            name=kwargs.get("name"),
        ).first()

    if existing:

        for key, value in kwargs.items():
            setattr(
                existing,
                key,
                value,
            )

        existing.save()

        return existing, None

    return Asset.objects.create(
        **kwargs
    ), None


@transaction.atomic
def generate_scene_video(
    *,
    scene,
    user,
    provider_code=None,
):

    project = scene.project

    storyboard = getattr(
        scene,
        "storyboard_image",
        None
    )

    if storyboard is None:
        raise RuntimeError(
            "La escena no tiene storyboard."
        )

    if (
        storyboard.status != "ready"
        or not storyboard.image_url
    ):
        raise RuntimeError(
            "Primero genera la imagen "
            "READY de esta escena."
        )

    provider = get_video_provider(
        provider_code
    )

    result = provider.generate(
        prompt=scene.video_prompt,
        project=project,
        scene=scene,
        image_url=storyboard.image_url,
    )

    if not result.success:
        raise RuntimeError(
            result.error
            or "Error generando video."
        )

    generation, generation_missing = (
        create_video_generation(
            user=user,
            project=project,
            scene=scene,
            storyboard=storyboard,
            provider=provider,
            result=result,
        )
    )

    asset, asset_missing = (
        create_video_asset(
            user=user,
            project=project,
            scene=scene,
            url=result.url,
        )
    )

    return {
        "scene": scene,
        "url": result.url,
        "provider": provider.code,
        "credit_cost":
            provider.credit_cost,
        "external_cost_usd":
            result.external_cost_usd,
        "generation":
            generation,
        "generation_missing_field":
            generation_missing,
        "asset":
            asset,
        "asset_missing_field":
            asset_missing,
        "is_mock":
            result.is_mock,
    }


def generate_all_scene_videos(
    *,
    project,
    user,
    provider_code=None,
):

    results = []

    for scene in (
        project.scenes
        .all()
        .order_by("position")
    ):

        results.append(
            generate_scene_video(
                scene=scene,
                user=user,
                provider_code=provider_code,
            )
        )

    return results
