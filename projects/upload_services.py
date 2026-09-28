import inspect

from config.storage import (
    save_project_image,
)

from generations import (
    image_services,
)


def _create_asset_compatible(
    *,
    project,
    scene,
    user,
    storyboard,
    image_url,
):
    function = getattr(
        image_services,
        "create_image_asset",
        None
    )

    if not callable(function):
        return None

    signature = inspect.signature(
        function
    )

    available = {
        "project": project,
        "scene": scene,
        "user": user,
        "owner": user,
        "storyboard": storyboard,
        "storyboard_image":
            storyboard,
        "url": image_url,
        "image_url": image_url,
        "source_url": image_url,
    }

    kwargs = {}

    for name, parameter in (
        signature.parameters.items()
    ):

        if name in available:
            kwargs[name] = (
                available[name]
            )
            continue

        if (
            parameter.default
            is not inspect.Parameter.empty
        ):
            continue

        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        # Unknown required argument.
        return None

    try:
        return function(
            **kwargs
        )
    except Exception:
        # Upload itself must not be lost
        # because Asset registration differs.
        return None


def save_scene_upload(
    *,
    project,
    scene,
    user,
    uploaded_file,
):
    saved = save_project_image(
        uploaded_file=uploaded_file,
        project_id=project.id,
        scene_position=scene.position,
    )

    try:
        storyboard = (
            scene.storyboard_image
        )
    except Exception:
        raise RuntimeError(
            "La escena no tiene "
            "StoryboardImage preparado."
        )

    storyboard.image_url = (
        saved["url"]
    )

    storyboard.status = "ready"

    update_fields = [
        "image_url",
        "status",
    ]

    if hasattr(
        storyboard,
        "updated_at"
    ):
        update_fields.append(
            "updated_at"
        )

    storyboard.save(
        update_fields=update_fields
    )

    asset = _create_asset_compatible(
        project=project,
        scene=scene,
        user=user,
        storyboard=storyboard,
        image_url=saved["url"],
    )

    return {
        "url": saved["url"],
        "path": saved["path"],
        "size": saved["size"],
        "format": saved["format"],
        "asset": asset,
    }
