from abc import ABC, abstractmethod
from dataclasses import dataclass
from html import escape
from pathlib import Path
import hashlib
import os

from django.conf import settings
from config.storage import save_generated_bytes, save_generated_text, storage_local_path
from .generation_profiles import get_generation_profile



def _use_unified_storage():
    """
    V47 gradual generated-storage rollout.

    legacy:
        /static/generated/...

    storage:
        Django default_storage
    """

    mode = (
        os.environ.get(
            "GINGAO_GENERATED_STORAGE_MODE",
            "legacy",
        )
        .strip()
        .lower()
    )

    return mode == "storage"



@dataclass

class VideoResult:
    success: bool
    url: str = ""
    provider: str = ""
    error: str = ""
    external_cost_usd: float = 0.0
    is_mock: bool = False


class VideoProvider(ABC):

    code = "base"
    display_name = "Base Video Provider"
    credit_cost = 0

    @abstractmethod
    def generate(
        self,
        *,
        prompt,
        project,
        scene,
        image_url="",
    ):
        raise NotImplementedError


class MockVideoProvider(VideoProvider):

    code = "mock"
    display_name = "Mock Video Provider"
    credit_cost = 0

    def generate(
        self,
        *,
        prompt,
        project,
        scene,
        image_url="",
    ):

        # GINGAO_MOCK_VIDEO_SEPARATE_OUTPUT_V40D2
        #
        # El storyboard puede servir como referencia visual,
        # pero el proveedor de video siempre debe devolver
        # un recurso propio y distinto de la imagen.
        #
        # No se consume ninguna API en modo mock.

        output_dir = (
            Path(settings.BASE_DIR)
            / "static"
            / "generated"
            / "video_mock"
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        seed = hashlib.sha256(
            (
                str(project.id)
                + ":"
                + str(scene.id)
                + ":"
                + prompt
            ).encode("utf-8")
        ).hexdigest()[:12]

        filename = (
            f"project_{project.id}_"
            f"scene_{scene.position}_"
            f"{seed}.svg"
        )

        path = output_dir / filename

        title = escape(
            str(project.title)[:40]
        )

        scene_text = escape(
            str(scene.script)[:130]
        )

        duration = max(
            int(scene.duration_seconds or 3),
            1
        )

        profile = get_generation_profile(
            project
        )

        width = profile["width"]
        height = profile["height"]

        svg = f"""
<svg xmlns="http://www.w3.org/2000/svg"
     width="{width}"
     height="{height}"
     viewBox="0 0 768 1365"
     preserveAspectRatio="xMidYMid slice">

    <defs>
        <linearGradient id="bg"
                        x1="0"
                        y1="0"
                        x2="1"
                        y2="1">

            <stop offset="0%"
                  stop-color="#efe8ff"/>

            <stop offset="50%"
                  stop-color="#ffdcca"/>

            <stop offset="100%"
                  stop-color="#fff3ae"/>

        </linearGradient>
    </defs>

    <rect width="768"
          height="1365"
          fill="url(#bg)"/>

    <g>

        <circle cx="225"
                cy="590"
                r="145"
                fill="#ef2349">

            <animateTransform
                attributeName="transform"
                type="translate"
                values="0,0; 16,-10; 0,0; -12,7; 0,0"
                dur="{duration}s"
                repeatCount="indefinite"/>

        </circle>

        <ellipse cx="525"
                 cy="570"
                 rx="105"
                 ry="235"
                 transform="rotate(14 525 570)"
                 fill="#ffd93d">

            <animateTransform
                attributeName="transform"
                type="rotate"
                values="14 525 570; 9 525 570; 17 525 570; 14 525 570"
                dur="{duration}s"
                repeatCount="indefinite"/>

        </ellipse>

    </g>

    <circle cx="185"
            cy="555"
            r="18"
            fill="white"/>

    <circle cx="255"
            cy="555"
            r="18"
            fill="white"/>

    <circle cx="185"
            cy="558"
            r="8"
            fill="#222"/>

    <circle cx="255"
            cy="558"
            r="8"
            fill="#222"/>

    <circle cx="490"
            cy="520"
            r="18"
            fill="white"/>

    <circle cx="550"
            cy="520"
            r="18"
            fill="white"/>

    <circle cx="490"
            cy="523"
            r="8"
            fill="#222"/>

    <circle cx="550"
            cy="523"
            r="8"
            fill="#222"/>

    <text x="50"
          y="95"
          font-family="Arial"
          font-size="23"
          font-weight="700"
          fill="#6954dc">
        GINGAO MOCK VIDEO
    </text>

    <text x="50"
          y="150"
          font-family="Arial"
          font-size="38"
          font-weight="800"
          fill="#17181b">
        {title}
    </text>

    <text x="50"
          y="1040"
          font-family="Arial"
          font-size="26"
          font-weight="800"
          fill="#17181b">
        ESCENA {scene.position} ? {duration}s
    </text>

    <foreignObject
        x="50"
        y="1080"
        width="660"
        height="190">

        <div xmlns="http://www.w3.org/1999/xhtml"
             style="
                font-family: Arial;
                font-size: 21px;
                line-height: 1.45;
                color: #555;
             ">
            {scene_text}
        </div>

    </foreignObject>

</svg>
"""

        if _use_unified_storage():

            stored = save_generated_text(
                category="video_mock",
                filename=filename,
                text=svg,
            )

            public_url = stored["url"]

        else:

            path.write_text(
                svg,
                encoding="utf-8"
            )

            public_url = (
                "/static/generated/video_mock/"
                + filename
            )

        return VideoResult(
            success=True,
            url=public_url,
            provider=self.code,
            external_cost_usd=0.0,
            is_mock=True,
        )



# =============================================================================
# GINGAO_REAL_VIDEO_PROVIDER_V44B
# =============================================================================

class FalVideoProvider(VideoProvider):

    code = "fal"
    display_name = "fal.ai Video"

    # Gingao credits are intentionally not charged here yet.
    # External billing will be connected after economic validation.
    credit_cost = 0

    default_model_id = (
        "alibaba/happy-horse/image-to-video"
    )

    def _model_id(self):

        return (
            os.environ.get(
                "GINGAO_FAL_VIDEO_MODEL",
                self.default_model_id,
            )
            .strip()
            or self.default_model_id
        )


    def _resolution_for_project(
        self,
        project,
    ):

        quality = str(
            getattr(
                project,
                "quality_tier",
                "standard",
            )
            or "standard"
        ).strip().lower()

        # Current provider supports 720p and 1080p.
        #
        # Final Gingao export may still render the complete
        # project at 1440p afterwards. The AI source clip
        # itself is capped here at the provider maximum.
        if quality == "fast":
            return "720p"

        return "1080p"


    def _duration_for_scene(
        self,
        scene,
    ):

        try:
            duration = int(
                getattr(
                    scene,
                    "duration_seconds",
                    5,
                )
                or 5
            )

        except (
            TypeError,
            ValueError,
        ):
            duration = 5

        # Current provider range: 3..15 seconds.
        return max(
            3,
            min(
                duration,
                15,
            ),
        )


    def _external_cost_estimate(
        self,
        *,
        resolution,
        duration,
        model_id,
    ):

        # Price estimate is only valid for the default
        # Happy Horse model.
        if (
            model_id
            != self.default_model_id
        ):
            return 0.0

        rates = {
            "720p": 0.14,
            "1080p": 0.28,
        }

        rate = rates.get(
            resolution,
            0.0,
        )

        return round(
            rate * duration,
            4,
        )


    def _persist_remote_video(
        self,
        *,
        remote_url,
        project,
        scene,
    ):
        """
        Download a real provider video and persist it through
        Django default_storage before database registration.

        This prevents VideoGeneration / Asset from depending
        directly on a provider-owned temporary URL.
        """

        import requests
        from uuid import uuid4

        max_bytes = 250 * 1024 * 1024

        with requests.get(
            remote_url,
            stream=True,
            timeout=(15, 180),
        ) as response:

            response.raise_for_status()

            content_type = str(
                response.headers.get(
                    "Content-Type",
                    ""
                )
                or ""
            ).lower()

            clean_url = str(
                remote_url
                or ""
            ).split(
                "?",
                1,
            )[0].lower()

            if (
                not content_type.startswith("video/")
                and not clean_url.endswith(
                    (
                        ".mp4",
                        ".mov",
                        ".webm",
                        ".m4v",
                    )
                )
            ):
                raise RuntimeError(
                    "fal.ai devolvio un recurso que "
                    "no parece ser video."
                )

            payload = bytearray()

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):
                if not chunk:
                    continue

                payload.extend(chunk)

                if len(payload) > max_bytes:
                    raise RuntimeError(
                        "El video generado supera el "
                        "limite seguro de 250 MB."
                    )

        if not payload:
            raise RuntimeError(
                "fal.ai devolvio un video vacio."
            )

        filename = (
            f"scene_{scene.position}_"
            f"{uuid4().hex[:16]}.mp4"
        )

        saved = save_generated_bytes(
            category="video_real",
            filename=filename,
            content=bytes(payload),
            project_id=project.pk,
        )

        durable_url = str(
            saved.get(
                "url",
                ""
            )
            or ""
        ).strip()

        if not durable_url:
            raise RuntimeError(
                "El storage guardo el video pero "
                "no devolvio una URL."
            )

        return durable_url


    def _local_image_path(
        self,
        image_url,
    ):
        """
        Resolve a Gingao local image URL into a filesystem path.

        Supported local sources:
        - legacy /static/...
        - default-storage /media/...

        Remote HTTP(S) URLs intentionally return None because
        _prepare_image_url() can pass those directly to fal.ai.
        """

        value = str(
            image_url
            or ""
        ).strip()

        if not value:
            return None

        if (
            value.startswith("http://")
            or value.startswith("https://")
        ):
            return None

        clean = value.split(
            "?",
            1,
        )[0]

        # -------------------------------------------------------------
        # V47K: Django default_storage / MEDIA_URL
        # -------------------------------------------------------------

        media_url = str(
            getattr(
                settings,
                "MEDIA_URL",
                "/media/",
            )
            or "/media/"
        )

        media_prefixes = [
            media_url,
            media_url.lstrip("/"),
        ]

        for prefix in media_prefixes:

            if (
                prefix
                and clean.startswith(
                    prefix
                )
            ):

                storage_name = (
                    clean[
                        len(prefix):
                    ]
                    .lstrip("/")
                )

                if not storage_name:
                    return None

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

        # -------------------------------------------------------------
        # Legacy static/generated compatibility
        # -------------------------------------------------------------

        static_prefixes = [
            "/static/",
            "static/",
        ]

        relative = None

        for prefix in static_prefixes:

            if clean.startswith(
                prefix
            ):
                relative = clean[
                    len(prefix):
                ]
                break

        if relative is None:
            return None

        path = (
            Path(settings.BASE_DIR)
            / "static"
            / relative
        )

        try:

            resolved = path.resolve()

            static_root = (
                Path(settings.BASE_DIR)
                / "static"
            ).resolve()

            resolved.relative_to(
                static_root
            )

        except (
            OSError,
            ValueError,
        ):
            return None

        if not resolved.exists():
            return None

        if not resolved.is_file():
            return None

        return resolved


    def _prepare_image_url(
        self,
        *,
        fal_client,
        image_url,
    ):

        value = str(
            image_url
            or ""
        ).strip()


        if (
            value.startswith(
                "http://"
            )
            or value.startswith(
                "https://"
            )
        ):
            return value


        local_path = (
            self._local_image_path(
                value
            )
        )


        if local_path is None:
            raise RuntimeError(
                "La imagen de storyboard no es una URL "
                "publica ni un archivo local disponible."
            )


        uploaded_url = (
            fal_client.upload_file(
                str(
                    local_path
                )
            )
        )


        if not uploaded_url:
            raise RuntimeError(
                "fal.ai no devolvio URL al subir "
                "la imagen de referencia."
            )


        return uploaded_url


    def generate(
        self,
        *,
        prompt,
        project,
        scene,
        image_url="",
    ):

        # ---------------------------------------------------------
        # SAFETY GATE
        # ---------------------------------------------------------
        #
        # Without FAL_KEY we exit BEFORE importing/calling fal.
        # Therefore merely registering this provider never
        # creates a paid request.

        fal_key = (
            os.environ.get(
                "FAL_KEY",
                ""
            )
            .strip()
        )


        if not fal_key:

            return VideoResult(
                success=False,
                provider=self.code,
                error=(
                    "FAL_KEY no esta configurada. "
                    "No se ha realizado ninguna "
                    "solicitud de pago."
                ),
                external_cost_usd=0.0,
                is_mock=False,
            )


        try:

            import fal_client

        except ImportError:

            return VideoResult(
                success=False,
                provider=self.code,
                error=(
                    "fal-client no esta instalado. "
                    "Ejecuta: pip install fal-client"
                ),
                external_cost_usd=0.0,
                is_mock=False,
            )


        model_id = (
            self._model_id()
        )

        resolution = (
            self._resolution_for_project(
                project
            )
        )

        duration = (
            self._duration_for_scene(
                scene
            )
        )


        try:

            remote_image_url = (
                self._prepare_image_url(
                    fal_client=fal_client,
                    image_url=image_url,
                )
            )


            arguments = {
                "image_url":
                    remote_image_url,

                "prompt":
                    str(
                        prompt
                        or ""
                    )[:2500],

                "resolution":
                    resolution,

                "duration":
                    duration,
            }


            result = (
                fal_client.subscribe(
                    model_id,
                    arguments=arguments,
                    with_logs=False,
                )
            )


            if not isinstance(
                result,
                dict,
            ):
                raise RuntimeError(
                    "fal.ai devolvio una respuesta "
                    "con formato inesperado."
                )


            video = result.get(
                "video",
                {}
            )


            if not isinstance(
                video,
                dict,
            ):
                raise RuntimeError(
                    "fal.ai no devolvio objeto video."
                )


            remote_url = str(
                video.get(
                    "url",
                    ""
                )
                or ""
            ).strip()


            if not remote_url:

                raise RuntimeError(
                    "fal.ai devolvio un video sin URL."
                )


            durable_url = (
                self._persist_remote_video(
                    remote_url=remote_url,
                    project=project,
                    scene=scene,
                )
            )


            estimated_cost = (
                self._external_cost_estimate(
                    resolution=resolution,
                    duration=duration,
                    model_id=model_id,
                )
            )


            return VideoResult(
                success=True,
                url=durable_url,
                provider=self.code,
                external_cost_usd=(
                    estimated_cost
                ),
                is_mock=False,
            )


        except Exception as exc:

            return VideoResult(
                success=False,
                provider=self.code,
                error=(
                    "Error fal.ai: "
                    + str(exc)
                ),
                external_cost_usd=0.0,
                is_mock=False,
            )



PROVIDERS = {
    "mock": MockVideoProvider,
    "fal": FalVideoProvider,
}


def get_video_provider(code=None):

    code = (
        code
        or os.environ.get(
            "GINGAO_VIDEO_PROVIDER",
            "mock"
        )
    ).strip().lower()

    provider_class = PROVIDERS.get(code)

    if provider_class is None:
        raise ValueError(
            f"Proveedor de video desconocido: {code}"
        )

    return provider_class()
