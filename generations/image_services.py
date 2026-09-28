from django.db import transaction

from assets_app.models import Asset
from projects.models import StoryboardImage

from .image_providers import get_image_provider


def _asset_kwargs(
    *,
    user,
    project,
    name,
    url,
):
    fields = {
        field.name: field
        for field in Asset._meta.fields
    }

    kwargs = {}

    values = {
        "owner": user,
        "user": user,
        "project": project,
        "name": name,
        "title": name,
        "kind": "image",
        "asset_type": "image",
        "type": "image",
        "url": url,
        "file_url": url,
        "source_url": url,
    }

    for key, value in values.items():
        if key in fields:
            kwargs[key] = value

    return kwargs


def _can_create_asset(kwargs):

    supplied = set(kwargs.keys())

    for field in Asset._meta.fields:

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

        return False

    return True


def create_image_asset(
    *,
    user,
    project,
    scene,
    url,
):
    name = (
        f"{project.title} - "
        f"Escena {scene.position}"
    )

    kwargs = _asset_kwargs(
        user=user,
        project=project,
        name=name,
        url=url,
    )

    if not _can_create_asset(kwargs):
        return None

    existing = None

    if "owner" in kwargs and "name" in kwargs:
        existing = Asset.objects.filter(
            owner=user,
            name=name,
        ).first()

    if existing:
        changed = False

        for field_name in [
            "url",
            "file_url",
            "source_url",
        ]:
            if (
                field_name in kwargs
                and hasattr(
                    existing,
                    field_name
                )
            ):
                setattr(
                    existing,
                    field_name,
                    url
                )
                changed = True

        if changed:
            existing.save()

        return existing

    return Asset.objects.create(
        **kwargs
    )


@transaction.atomic
def generate_storyboard_image(
    *,
    storyboard,
    user,
    provider_code=None,
):

    scene = storyboard.scene
    project = scene.project

    provider = get_image_provider(
        provider_code
    )

    result = provider.generate(
        prompt=storyboard.prompt,
        project=project,
        scene=scene,
    )

    if not result.success:
        storyboard.status = "failed"
        storyboard.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        raise RuntimeError(
            result.error
            or "Error generando imagen."
        )

    storyboard.image_url = result.url
    storyboard.status = "ready"

    storyboard.save(
        update_fields=[
            "image_url",
            "status",
            "updated_at",
        ]
    )

    asset = create_image_asset(
        user=user,
        project=project,
        scene=scene,
        url=result.url,
    )

    return {
        "storyboard": storyboard,
        "asset": asset,
        "provider": result.provider,
        "credit_cost": provider.credit_cost,
        "external_cost_usd": result.external_cost_usd,
    }


def generate_all_storyboard_images(
    *,
    project,
    user,
    provider_code=None,
):

    results = []

    storyboard_items = (
        StoryboardImage.objects
        .filter(
            scene__project=project
        )
        .select_related(
            "scene",
            "scene__project",
        )
        .order_by(
            "scene__position"
        )
    )

    for storyboard in storyboard_items:

        results.append(
            generate_storyboard_image(
                storyboard=storyboard,
                user=user,
                provider_code=provider_code,
            )
        )

    return results
