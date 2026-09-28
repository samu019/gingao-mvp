import tempfile
import json
import subprocess
import shutil
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage

import imageio_ffmpeg

from assets_app.models import Asset
from generations.models import VideoGeneration
from generations.audio_services import get_project_audio_info
from config.storage import save_generated_bytes, storage_local_path



def _use_unified_final_storage():
    """
    V47 gradual storage rollout.

    legacy:
        persistent final MP4 under static/generated.

    storage:
        render locally, then persist with default_storage.
    """

    import os

    mode = (
        os.environ.get(
            "GINGAO_GENERATED_STORAGE_MODE",
            "legacy",
        )
        .strip()
        .lower()
    )

    return mode == "storage"


# GINGAO_PROJECT_OUTPUT_SPEC_V39A
# GINGAO_REAL_QUALITY_TIERS_V39C

QUALITY_RENDER_PROFILES = {
    "fast": {
        "label": "economica",
        "crf": 25,
        "preset": "veryfast",
        "dimensions": {
            "9:16": (720, 1280),
            "16:9": (1280, 720),
            "1:1": (720, 720),
            "4:5": (720, 900),
        },
    },
    "standard": {
        "label": "estandar",
        "crf": 20,
        "preset": "medium",
        "dimensions": {
            "9:16": (1080, 1920),
            "16:9": (1920, 1080),
            "1:1": (1080, 1080),
            "4:5": (1080, 1350),
        },
    },
    "premium": {
        "label": "premium",
        "crf": 17,
        "preset": "slow",
        "dimensions": {
            "9:16": (1440, 2560),
            "16:9": (2560, 1440),
            "1:1": (1440, 1440),
            "4:5": (1440, 1800),
        },
    },
}


def get_project_output_spec(
    project,
    quality_override=None,
):
    ratio = str(
        getattr(
            project,
            "aspect_ratio",
            "9:16",
        )
        or "9:16"
    ).strip()

    if ratio not in {
        "9:16",
        "16:9",
        "1:1",
        "4:5",
    }:
        ratio = "9:16"

    quality = str(
        quality_override
        or getattr(
            project,
            "quality_tier",
            "standard",
        )
        or "standard"
    ).strip().lower()

    if quality not in QUALITY_RENDER_PROFILES:
        quality = "standard"

    profile = (
        QUALITY_RENDER_PROFILES[
            quality
        ]
    )

    width, height = (
        profile["dimensions"][
            ratio
        ]
    )

    return {
        "aspect_ratio": ratio,
        "quality_tier": quality,
        "quality_label":
            profile["label"],
        "width": width,
        "height": height,
        "fps": 30,
        "crf": profile["crf"],
        "preset": profile["preset"],
    }




def _field_names(model):
    return {
        field.name: field
        for field in model._meta.fields
    }


def _required_fields_satisfied(
    model,
    kwargs,
):
    fields = _field_names(model)

    supplied = set(kwargs.keys())

    for field in model._meta.fields:

        if field.primary_key:
            continue

        if field.name in supplied:
            continue

        if field.auto_created:
            continue

        if getattr(field, "auto_now", False):
            continue

        if getattr(field, "auto_now_add", False):
            continue

        if field.has_default():
            continue

        if field.null:
            continue

        if field.blank:
            continue

        from django.db import models

        if isinstance(
            field,
            models.BooleanField
        ):
            continue

        return False, field.name

    return True, None


def _generation_url(generation):

    if generation is None:
        return ""

    for field_name in [
        "output_url",
        "video_url",
        "url",
        "file_url",
    ]:

        if hasattr(
            generation,
            field_name
        ):
            value = getattr(
                generation,
                field_name
            )

            if value:
                return value

    return ""



# ============================================================================
# GINGAO V33 HELPERS
# ============================================================================

def _storage_name_from_media_url(
    url,
):
    """
    Convert a MEDIA_URL reference to a storage-relative name.
    """

    value = str(
        url
        or ""
    ).strip()

    if not value:
        return None

    clean = value.split(
        "?",
        1,
    )[0]

    media_url = str(
        getattr(
            settings,
            "MEDIA_URL",
            "/media/",
        )
        or "/media/"
    )

    prefixes = [
        media_url,
        media_url.lstrip("/"),
    ]

    for prefix in prefixes:

        if (
            prefix
            and clean.startswith(
                prefix
            )
        ):

            name = (
                clean[
                    len(prefix):
                ]
                .lstrip("/")
            )

            return (
                name
                or None
            )

    return None


def _url_suffix(
    url,
):
    clean = str(
        url
        or ""
    ).split(
        "?",
        1,
    )[0]

    return Path(
        clean
    ).suffix.lower()


def _url_to_local_path(
    url,
):
    """
    Resolve an already-local resource.

    For Django media storage, return a physical path only
    when the active backend exposes one.

    Remote object storage therefore returns None here.
    """

    if not url:
        return None

    value = str(
        url
    ).strip()

    if (
        value.startswith("http://")
        or value.startswith("https://")
    ):
        return None

    clean = value.split(
        "?",
        1,
    )[0]

    if clean.startswith(
        "/static/"
    ):

        rel = clean[
            len("/static/"):
        ]

        path = (
            Path(settings.BASE_DIR)
            / "static"
            / rel
        )

        return (
            path
            if path.exists()
            else None
        )

    if clean.startswith(
        "static/"
    ):

        rel = clean[
            len("static/"):
        ]

        path = (
            Path(settings.BASE_DIR)
            / "static"
            / rel
        )

        return (
            path
            if path.exists()
            else None
        )

    storage_name = (
        _storage_name_from_media_url(
            clean
        )
    )

    if storage_name:

        local_path = (
            storage_local_path(
                storage_name
            )
        )

        if (
            local_path is not None
            and local_path.exists()
            and local_path.is_file()
        ):
            return local_path

        return None

    possible = Path(
        clean
    )

    if (
        possible.exists()
        and possible.is_file()
    ):
        return possible

    return None


def _url_resource_exists(
    url,
):
    """
    Existence check without forcing a remote download.
    """

    local_path = (
        _url_to_local_path(
            url
        )
    )

    if (
        local_path is not None
        and local_path.exists()
    ):
        return True

    storage_name = (
        _storage_name_from_media_url(
            url
        )
    )

    if storage_name:

        try:
            return default_storage.exists(
                storage_name
            )
        except Exception:
            return False

    return False


def _materialize_url_to_local_path(
    url,
    *,
    workdir,
    label="resource",
):
    """
    Return a physical file suitable for FFmpeg.

    Local FileSystemStorage:
        reuse the existing physical path.

    Remote storage:
        copy the object into the render TemporaryDirectory.
    """

    local_path = (
        _url_to_local_path(
            url
        )
    )

    if (
        local_path is not None
        and local_path.exists()
        and local_path.is_file()
    ):
        return local_path

    storage_name = (
        _storage_name_from_media_url(
            url
        )
    )

    if not storage_name:
        return None

    if not default_storage.exists(
        storage_name
    ):
        return None

    suffix = (
        Path(storage_name)
        .suffix
    )

    if not suffix:
        suffix = ".bin"

    safe_label = "".join(
        char
        if (
            char.isalnum()
            or char in "-_"
        )
        else "_"
        for char in str(label)
    )

    destination = (
        Path(workdir)
        / (
            "materialized_"
            + safe_label
            + "_"
            + uuid4().hex[:12]
            + suffix
        )
    )

    with default_storage.open(
        storage_name,
        "rb",
    ) as source:

        with destination.open(
            "wb",
        ) as target:

            shutil.copyfileobj(
                source,
                target,
            )

    if (
        not destination.exists()
        or destination.stat().st_size <= 0
    ):
        try:
            destination.unlink()
        except OSError:
            pass

        return None

    return destination


def _timeline_preview_url(item):
    """
    Devuelve la mejor imagen de respaldo para una escena.
    Prioridad:
    1) preview_url
    2) scene.storyboard_image.image_url
    """
    preview_url = item.get("preview_url") or ""
    if preview_url:
        return preview_url

    scene = item.get("scene")
    if scene is not None:
        try:
            storyboard = scene.storyboard_image
            if storyboard and getattr(storyboard, "image_url", ""):
                return storyboard.image_url
        except Exception:
            pass

    return ""


def _render_image_scene_clip(
    *,
    ffmpeg_exe,
    image_path,
    output_path,
    duration,
    width=1080,
    height=1920,
    fps=30,
    preset="medium",
    crf=20,
):
    """
    Genera un clip MP4 desde una imagen con un movimiento suave
    tipo Ken Burns (zoom + pan muy ligero).
    """
    import subprocess

    total_frames = max(int(duration * fps), fps)
    safe_image = str(image_path).replace("\\", "/")
    safe_output = str(output_path).replace("\\", "/")

    zoom_expr = (
        "zoompan="
        "z='min(zoom+0.0008,1.12)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        f"d={total_frames}:"
        f"s={width}x{height}:"
        f"fps={fps}"
    )

    vf = (
        f"scale={width}:{height}:"
        "force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"{zoom_expr},"
        "setsar=1,"
        "format=yuv420p"
    )

    cmd = [
        ffmpeg_exe,
        "-y",
        "-loop", "1",
        "-i", safe_image,
        "-t", str(duration),
        "-r", str(fps),
        "-vf", vf,
        "-an",
        "-c:v", "libx264",
        "-preset", str(preset),
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        safe_output,
    ]

    subprocess.run(cmd, check=True)


def _render_fallback_scene_clip(
    *,
    ffmpeg_exe,
    output_path,
    scene_number,
    duration,
    width=1080,
    height=1920,
    fps=30,
    preset="medium",
    crf=20,
):
    """
    Fallback limpio cuando falta visual.
    """
    import subprocess

    safe_output = str(output_path).replace("\\", "/")
    label = f"Escena {scene_number}"

    vf = (
        f"color=c=#10141f:s={width}x{height}:d={duration},"
        f"drawbox=x=60:y=120:w={width-120}:h={height-240}:color=#1a2233:t=fill,"
        f"drawtext=text='{label}':fontcolor=white:fontsize=54:x=(w-text_w)/2:y=(h-text_h)/2-40,"
        f"drawtext=text='Visual pendiente':fontcolor=#a9b7d1:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2+40,"
        "format=yuv420p"
    )

    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "lavfi",
        "-i", vf,
        "-t", str(duration),
        "-r", str(fps),
        "-an",
        "-c:v", "libx264",
        "-preset", str(preset),
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        safe_output,
    ]

    subprocess.run(cmd, check=True)


def _render_scene_visual_clip(
    *,
    ffmpeg_exe,
    item,
    workdir,
    width=1080,
    height=1920,
    fps=30,
    preset="medium",
    crf=20,
):
    """
    Devuelve un clip mp4 listo para concatenar:
    - usa v?deo si existe;
    - si no, genera v?deo desde imagen;
    - si no, usa fallback.
    """
    import subprocess
    import shutil

    scene = item["scene"]
    duration = int(item.get("duration") or getattr(scene, "duration_seconds", 1) or 1)
    scene_no = getattr(scene, "position", 0) or 0

    clip_path = Path(workdir) / f"scene_{scene_no:02d}.mp4"

    # 1) Solo archivos de video reales.
    # Los SVG de video_mock son artefactos tecnicos,
    # no fuentes reproducibles para FFmpeg.

    video_url = item.get("url") or ""

    video_path = _materialize_url_to_local_path(
        video_url,
        workdir=workdir,
        label=f"scene_{scene_no}_video",
    )

    video_extensions = {
        ".mp4",
        ".mov",
        ".m4v",
        ".webm",
        ".mkv",
        ".avi",
    }

    valid_video = (
        video_path
        and video_path.exists()
        and video_path.suffix.lower()
        in video_extensions
    )

    if valid_video:

        cmd = [
            ffmpeg_exe,
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(video_path),
            "-t",
            str(duration),
            "-r",
            str(fps),
            "-vf",
            (
                f"scale={width}:{height}:"
                "force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:"
                "(ow-iw)/2:(oh-ih)/2:"
                "color=0x0f1523,"
                "setsar=1,"
                "format=yuv420p"
            ),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            str(preset),
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            str(clip_path),
        ]

        subprocess.run(
            cmd,
            check=True
        )

        return clip_path

    # 2) imagen real/storyboard
    preview_url = _timeline_preview_url(
        item
    )

    preview_path = _materialize_url_to_local_path(
        preview_url,
        workdir=workdir,
        label=f"scene_{scene_no}_image",
    )

    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
    }

    valid_image = (
        preview_path
        and preview_path.exists()
        and preview_path.suffix.lower()
        in image_extensions
    )

    if valid_image:

        _render_image_scene_clip(
            ffmpeg_exe=ffmpeg_exe,
            image_path=preview_path,
            output_path=clip_path,
            duration=duration,
            width=width,
            height=height,
            fps=fps,
            preset=preset,
            crf=crf,
        )

        return clip_path

    # 3) fallback elegante
    _render_fallback_scene_clip(
        ffmpeg_exe=ffmpeg_exe,
        output_path=clip_path,
        scene_number=scene_no,
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        preset=preset,
        crf=crf,
    )
    return clip_path

def get_project_video_timeline(project):

    generations = (
        VideoGeneration.objects
        .filter(
            scene__project=project
        )
        .order_by(
            "scene_id",
            "-pk",
        )
    )

    latest = {}

    for generation in generations:

        if generation.scene_id not in latest:
            latest[
                generation.scene_id
            ] = generation

    timeline = []

    elapsed = 0

    for scene in (
        project.scenes
        .all()
        .order_by("position")
    ):

        generation = latest.get(
            scene.id
        )

        url = _generation_url(
            generation
        )

        # GINGAO_FINAL_PREVIEW_SOURCE_V17
        #
        # Technical Mock assets are valid for backend testing,
        # but must never look like the finished video preview.
        preview_url = url or ""

        def _is_mock_asset(value):
            value = str(value or "")
            return (
                "/static/generated/video_mock/" in value
                or "/static/generated/mock/" in value
            )

        storyboard_url = ""

        try:
            storyboard = scene.storyboard_image
            storyboard_url = (
                getattr(
                    storyboard,
                    "image_url",
                    "",
                )
                or ""
            )
        except Exception:
            storyboard_url = ""

        # If the generated video is Mock, prefer a real
        # uploaded/generated storyboard image.
        if _is_mock_asset(preview_url):

            if (
                storyboard_url
                and not _is_mock_asset(
                    storyboard_url
                )
            ):
                preview_url = storyboard_url

            else:
                # No professional visual exists yet.
                # Template will render a branded placeholder.
                preview_url = ""


        duration = int(
            scene.duration_seconds
            or 1
        )

        timeline.append({
            "scene": scene,
            "generation": generation,
            "url": url,
            "preview_url": preview_url,
            "duration": duration,
            "start": elapsed,
            "end": elapsed + duration,
            "ready": bool(url),
        })

        elapsed += duration

    return timeline, elapsed


def _create_final_asset(
    *,
    project,
    user,
    url,
):
    fields = _field_names(
        Asset
    )

    name = (
        f"{project.title} - Corte final"
    )

    candidates = {
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

    for key, value in candidates.items():

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

    existing = None

    if (
        "owner" in fields
        and "name" in fields
    ):
        existing = (
            Asset.objects
            .filter(
                owner=user,
                name=name,
            )
            .first()
        )

    if existing:

        for key, value in kwargs.items():
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


def create_mock_final_cut(
    *,
    project,
    user,
):
    timeline, duration = (
        get_project_video_timeline(
            project
        )
    )

    # GINGAO_FINAL_EXPORT_AUDIO_V31
    audio_info = get_project_audio_info(
        project=project,
        user=user,
    )

    audio_url = (
        audio_info.get("url")
        or ""
    )


    missing = [
        item["scene"].position
        for item in timeline
        if not item["ready"]
    ]

    if missing:
        raise RuntimeError(
            "Faltan videos en las escenas: "
            + ", ".join(
                str(value)
                for value in missing
            )
        )

    output_dir = (
        Path(settings.BASE_DIR)
        / "static"
        / "generated"
        / "final_mock"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = (
        f"project_{project.id}_"
        f"{uuid4().hex[:12]}.json"
    )

    destination = (
        output_dir
        / filename
    )

    manifest = {
        "type": "gingao_mock_final_cut",
        "version": 2,

        "project": {
            "id": project.id,
            "title": project.title,
            "format": "9:16",
            "target_duration_seconds":
                getattr(
                    project,
                    "target_duration_seconds",
                    duration,
                ),
        },

        "export": {
            "provider": "mock",
            "status": "prepared",
            "duration_seconds": duration,
            "scene_count": len(timeline),
            "has_audio": bool(audio_url),
        },

        "audio": {
            "url": audio_url,
            "duration_seconds": duration,
            "provider": (
                "mock"
                if audio_url
                else None
            ),
            "synchronized": bool(audio_url),
            "start_seconds": 0,
            "end_seconds": duration,
        },

        "timeline": [
            {
                "position":
                    item["scene"].position,

                "duration_seconds":
                    item["duration"],

                "start_seconds":
                    item["start"],

                "end_seconds":
                    item["end"],

                "video_url":
                    item["url"],

                "preview_url":
                    item.get(
                        "preview_url",
                        "",
                    ),

                "script":
                    item["scene"].script,

                "video_prompt":
                    item["scene"].video_prompt,

                "ready":
                    bool(
                        item["ready"]
                    ),
            }
            for item in timeline
        ],
    }

    destination.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8"
    )

    public_url = (
        "/static/generated/final_mock/"
        + filename
    )

    asset, asset_missing = (
        _create_final_asset(
            project=project,
            user=user,
            url=public_url,
        )
    )

    return {
        "url": public_url,
        "path": destination,
        "duration": duration,
        "timeline": timeline,
        "audio_url": audio_url,
        "has_audio": bool(audio_url),
        "asset": asset,
        "asset_missing_field":
            asset_missing,
    }


# =====================================================================
# GINGAO_REAL_LOCAL_MP4_EXPORT_V32
# =====================================================================

def _run_ffmpeg(
    command,
    *,
    label,
):
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if process.returncode != 0:

        tail = (
            process.stderr
            or process.stdout
            or ""
        )[-3500:]

        raise RuntimeError(
            f"FFmpeg fallo en {label}: "
            f"{tail}"
        )

    return process


def create_local_final_mp4(
    *,
    project,
    user,
    quality_tier=None,
):
    """
    GINGAO V33 real local export.

    Uses:
    - real video when available;
    - animated image / storyboard fallback;
    - elegant placeholder only as last resort;
    - synchronized narration audio;
    - V31 technical manifest.
    """

    manifest_result = (
        create_mock_final_cut(
            project=project,
            user=user,
        )
    )

    timeline, duration = (
        get_project_video_timeline(
            project
        )
    )

    if not timeline:
        raise RuntimeError(
            "El proyecto no tiene escenas."
        )

    voice_enabled = bool(
        getattr(
            project,
            "voice_enabled",
            True,
        )
    )

    if voice_enabled:
        audio_info = (
            get_project_audio_info(
                project=project,
                user=user,
            )
        )
    else:
        audio_info = {
            "asset": None,
            "url": "",
            "disabled": True,
        }

    result = render_real_final_mp4(
        project=project,
        timeline=timeline,
        total_duration=duration,
        audio_info=audio_info,
        quality_tier=quality_tier,
    )

    public_url = result["url"]

    asset, asset_missing = (
        _create_final_asset(
            project=project,
            user=user,
            url=public_url,
        )
    )

    return {
        "url": public_url,
        "path": result["path"],
        "duration": duration,
        "timeline": timeline,
        "audio_url": (
            audio_info.get("url")
            or ""
        ),
        "has_audio": result["has_audio"],
        "asset": asset,
        "asset_missing_field":
            asset_missing,
        "manifest_url":
            manifest_result["url"],
        "width": result["width"],
        "height": result["height"],
        "aspect_ratio": result["aspect_ratio"],
        "quality_tier": result["quality_tier"],
        "render_preset": result["preset"],
        "render_crf": result["crf"],
        "fps": result["fps"],
        "video_codec": "h264",
        "audio_codec": (
            "aac"
            if result["has_audio"]
            else None
        ),
        "renderer": "v33_local_scene_completion",
    }

def render_real_final_mp4(
    project,
    timeline,
    total_duration,
    audio_info=None,
    quality_tier=None,
):
    """
    Render final local usando:
    - v?deo de escena si existe
    - imagen animada local si no existe v?deo
    - fallback si no hay nada
    """
    import os
    import subprocess
    import tempfile
    import uuid
    from django.conf import settings
    import imageio_ffmpeg

    storage_mode = (
        _use_unified_final_storage()
    )

    final_name = (
        f"project_{project.id}_"
        f"{uuid.uuid4().hex[:12]}.mp4"
    )

    if storage_mode:

        final_path = None
        final_url = ""

    else:

        output_dir = (
            Path(settings.BASE_DIR)
            / "static"
            / "generated"
            / "final_video"
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        final_path = (
            output_dir
            / final_name
        )

        final_url = (
            "/static/generated/"
            "final_video/"
            + final_name
        )

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    output_spec = get_project_output_spec(
        project,
        quality_override=quality_tier,
    )

    width = output_spec["width"]
    height = output_spec["height"]
    fps = output_spec["fps"]
    aspect_ratio = output_spec["aspect_ratio"]
    quality_tier = output_spec["quality_tier"]
    preset = output_spec["preset"]
    crf = output_spec["crf"]

    with tempfile.TemporaryDirectory(prefix="gingao_final_") as tmpdir:
        tmpdir = Path(tmpdir)

        if storage_mode:

            final_path = (
                tmpdir
                / final_name
            )

        scene_clips = []
        for item in timeline:
            clip = _render_scene_visual_clip(
                ffmpeg_exe=ffmpeg_exe,
                item=item,
                workdir=tmpdir,
                width=width,
                height=height,
                fps=fps,
                preset=preset,
                crf=crf,
            )
            scene_clips.append(clip)

        concat_file = tmpdir / "concat.txt"
        concat_file.write_text(
            "\n".join(
                f"file '{str(p).replace(chr(92), '/')}'"
                for p in scene_clips
            ),
            encoding="utf-8",
        )

        merged_video = tmpdir / "merged.mp4"

        subprocess.run([
            ffmpeg_exe,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:v", "libx264",
            "-preset", str(preset),
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            str(merged_video),
        ], check=True)

        audio_url = ""
        if audio_info and isinstance(audio_info, dict):
            audio_url = audio_info.get("url", "") or ""

        audio_path = _materialize_url_to_local_path(
            audio_url,
            workdir=tmpdir,
            label="final_audio",
        )

        if audio_path and audio_path.exists():
            subprocess.run([
                ffmpeg_exe,
                "-y",
                "-i", str(merged_video),
                "-i", str(audio_path),
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                str(final_path),
            ], check=True)
            has_audio = True
        else:
            merged_video.replace(final_path)
            has_audio = False

        if storage_mode:

            if (
                not final_path.exists()
                or final_path.stat().st_size
                <= 0
            ):
                raise RuntimeError(
                    "Final MP4 was not created."
                )

            stored = save_generated_bytes(
                category="final_video",
                filename=final_name,
                content=final_path.read_bytes(),
                project_id=project.id,
            )

            final_url = stored["url"]

            persistent_path = (
                storage_local_path(
                    stored["name"]
                )
            )

        else:

            persistent_path = final_path

    return {
        "url": final_url,
        "path": (
            str(persistent_path)
            if persistent_path is not None
            else ""
        ),
        "duration": total_duration,
        "has_audio": has_audio,
        "width": width,
        "height": height,
        "aspect_ratio": aspect_ratio,
        "quality_tier": quality_tier,
        "preset": preset,
        "crf": crf,
        "fps": fps,
    }


# ============================================================================
# GINGAO_REAL_VISUAL_COVERAGE_V34
# ============================================================================

def get_project_visual_coverage(
    project
):
    """
    Classify every scene as:
    - video: real local video
    - image: real raster image
    - mock: technical SVG/mock source only
    - missing: no usable visual

    Returns scene-level information plus project totals.
    """

    timeline, total_duration = (
        get_project_video_timeline(
            project
        )
    )

    video_extensions = {
        ".mp4",
        ".mov",
        ".m4v",
        ".webm",
        ".mkv",
        ".avi",
    }

    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
    }

    scenes = []

    real_count = 0
    mock_count = 0
    missing_count = 0

    for item in timeline:

        scene = item["scene"]

        video_url = (
            item.get("url")
            or ""
        )

        preview_url = (
            _timeline_preview_url(
                item
            )
            or ""
        )

        video_path = (
            _url_to_local_path(
                video_url
            )
        )

        preview_path = (
            _url_to_local_path(
                preview_url
            )
        )

        status = "missing"
        source_type = "none"
        source_url = ""

        if (
            _url_resource_exists(
                video_url
            )
            and _url_suffix(
                video_url
            )
            in video_extensions
        ):

            status = "real"
            source_type = "video"
            source_url = video_url
            real_count += 1

        elif (
            _url_resource_exists(
                preview_url
            )
            and _url_suffix(
                preview_url
            )
            in image_extensions
        ):

            status = "real"
            source_type = "image"
            source_url = preview_url
            real_count += 1

        elif (
            str(video_url).lower().endswith(
                ".svg"
            )
            or str(
                preview_url
            ).lower().endswith(
                ".svg"
            )
        ):

            status = "mock"
            source_type = "mock"
            source_url = (
                preview_url
                or video_url
            )
            mock_count += 1

        else:

            missing_count += 1

        scenes.append({
            "scene": scene,
            "position":
                scene.position,
            "duration":
                item["duration"],
            "status":
                status,
            "source_type":
                source_type,
            "source_url":
                source_url,
            "is_real":
                status == "real",
            "is_mock":
                status == "mock",
            "is_missing":
                status == "missing",
        })

    scene_count = len(
        scenes
    )

    percent = (
        round(
            real_count
            / scene_count
            * 100
        )
        if scene_count
        else 0
    )

    return {
        "scenes": scenes,
        "scene_count":
            scene_count,
        "real_count":
            real_count,
        "mock_count":
            mock_count,
        "missing_count":
            missing_count,
        "real_percent":
            percent,
        "total_duration":
            total_duration,
        "complete":
            (
                scene_count > 0
                and real_count
                == scene_count
            ),
    }

