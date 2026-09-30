from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return None

    return dictionary.get(key)



@register.filter
def project_cover(project):
    """
    Return first ready storyboard image
    for a project.
    """

    try:

        scenes = (
            project.scenes
            .all()
            .order_by("position")
        )

        for scene in scenes:

            try:
                storyboard = (
                    scene.storyboard_image
                )
            except Exception:
                continue

            url = (
                getattr(
                    storyboard,
                    "image_url",
                    ""
                )
                or ""
            )

            status = (
                getattr(
                    storyboard,
                    "status",
                    ""
                )
            )

            if (
                url
                and status == "ready"
            ):
                return url

    except Exception:
        pass

    return ""



@register.filter
def asset_preview(asset):
    """
    Finds the best available URL without coupling
    the template to one historical Asset schema.
    """

    candidates = [
        "file_url",
        "url",
        "image_url",
        "video_url",
        "audio_url",
        "source_url",
        "preview_url",
        "thumbnail_url",
        "file",
    ]

    for name in candidates:

        try:
            value = getattr(asset, name, None)
        except Exception:
            continue

        if not value:
            continue

        # Django FileField / FieldFile
        try:
            field_url = getattr(value, "url", None)

            if field_url:
                return str(field_url)
        except Exception:
            pass

        if isinstance(value, str):
            return value

    return ""


@register.filter
def asset_kind(asset):

    for name in [
        "asset_type",
        "kind",
        "type",
        "media_type",
    ]:

        try:
            value = getattr(asset, name, None)
        except Exception:
            value = None

        if value:
            value = str(value).lower()

            if "video" in value:
                return "video"

            if "image" in value:
                return "image"

            if (
                "audio" in value
                or "voice" in value
            ):
                return "audio"

            if "character" in value:
                return "character"

    return "asset"


@register.filter
def asset_preview_mode(asset):

    url = asset_preview(asset)
    kind = asset_kind(asset)

    clean = (
        str(url)
        .lower()
        .split("?")[0]
    )

    if (
        kind == "video"
        and clean.endswith(
            (
                ".mp4",
                ".webm",
                ".ogg",
                ".mov",
            )
        )
    ):
        return "video"

    if clean.endswith(
        (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif",
            ".svg",
        )
    ):
        return "image"

    # Mock video SVGs can still render as images.
    if kind == "video" and url:
        return "image"

    return "fallback"



# GINGAO_ASSET_CLASSIFICATION_V2

@register.filter
def asset_is_demo(asset):
    """
    Development/mock assets must be clearly identified.
    """

    try:
        url = str(
            getattr(
                asset,
                "source_url",
                ""
            )
            or ""
        ).lower()
    except Exception:
        url = ""

    return (
        "/generated/mock/" in url
        or "/generated/video_mock/" in url
        or "/mock/" in url
    )


@register.filter
def asset_origin(asset):

    try:
        url = str(
            getattr(
                asset,
                "source_url",
                ""
            )
            or ""
        ).lower()
    except Exception:
        url = ""

    if (
        "/generated/mock/" in url
        or "/generated/video_mock/" in url
        or "/mock/" in url
    ):
        return "demo"

    if "/generated/uploads/" in url:
        return "uploaded"

    if "/generated/fal/" in url:
        return "generated"

    if url:
        return "generated"

    return "unknown"


@register.filter
def asset_display_name(asset):

    value = getattr(
        asset,
        "name",
        ""
    )

    if value:
        return str(value)

    return "Activo sin nombre"



# GINGAO_PROJECT_STATUS_FILTERS_V1

def _project_status_value(project):
    value = getattr(
        project,
        "status",
        ""
    )

    return str(
        value or ""
    ).strip().lower()


@register.filter
def project_progress(project):

    status = _project_status_value(
        project
    )

    mapping = {
        "script": 25,
        "guion": 25,
        "gui?n": 25,

        "images": 50,
        "image": 50,
        "imagenes": 50,
        "im?genes": 50,

        "video": 75,
        "v?deo": 75,

        "final": 100,
        "final_cut": 100,
        "final cut": 100,
        "corte final": 100,
    }

    return mapping.get(
        status,
        10
    )


@register.filter
def project_stage_label(project):

    status = _project_status_value(
        project
    )

    mapping = {
        "script": "GUI\u00d3N",
        "guion": "GUI\u00d3N",
        "gui?n": "GUI\u00d3N",

        "images": "IM\u00c1GENES",
        "image": "IM\u00c1GENES",
        "imagenes": "IM\u00c1GENES",
        "im?genes": "IM\u00c1GENES",

        "video": "V\u00cdDEO",
        "v?deo": "V\u00cdDEO",

        "final": "FINAL",
        "final_cut": "FINAL",
        "final cut": "FINAL",
        "corte final": "FINAL",
    }

    return mapping.get(
        status,
        str(
            getattr(
                project,
                "status",
                "PROYECTO"
            )
        ).upper()
    )


@register.filter
def project_stage_number(project):

    progress = project_progress(
        project
    )

    if progress >= 100:
        return 4

    if progress >= 75:
        return 3

    if progress >= 50:
        return 2

    if progress >= 25:
        return 1

    return 0
