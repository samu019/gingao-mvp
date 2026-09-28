from abc import ABC, abstractmethod
from dataclasses import dataclass
from html import escape
from pathlib import Path
import hashlib
import os
import urllib.request

from django.conf import settings
from config.storage import save_generated_bytes, save_generated_text
from .generation_profiles import get_generation_profile



def _use_unified_storage():
    """
    Gradual V47 storage rollout.

    legacy:
        current /static/generated behavior.

    storage:
        Django default_storage.
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

class ImageResult:
    success: bool
    url: str = ""
    provider: str = ""
    error: str = ""
    external_cost_usd: float = 0.0


class ImageProvider(ABC):

    code = "base"
    display_name = "Base Provider"

    # Por ahora no descontamos créditos Gingao
    # hasta validar el proveedor real.
    credit_cost = 0

    @abstractmethod
    def generate(self, *, prompt, project, scene):
        raise NotImplementedError


class MockImageProvider(ImageProvider):

    code = "mock"
    display_name = "Mock Provider"
    credit_cost = 0

    def generate(self, *, prompt, project, scene):

        output_dir = (
            Path(settings.BASE_DIR)
            / "static"
            / "generated"
            / "mock"
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
        ).hexdigest()[:10]

        filename = (
            f"project_{project.id}_"
            f"scene_{scene.position}_"
            f"{seed}.svg"
        )

        path = output_dir / filename

        title = escape(
            str(project.title)[:45]
        )

        scene_text = escape(
            str(scene.script)[:120]
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
                  stop-color="#f4eaff"/>
            <stop offset="50%"
                  stop-color="#ffe6d2"/>
            <stop offset="100%"
                  stop-color="#fff5b5"/>
        </linearGradient>
    </defs>

    <rect width="768"
          height="1365"
          rx="36"
          fill="url(#bg)"/>

    <circle cx="220"
            cy="585"
            r="150"
            fill="#ef2349"/>

    <ellipse cx="520"
             cy="565"
             rx="105"
             ry="245"
             transform="rotate(14 520 565)"
             fill="#ffd93d"/>

    <circle cx="180"
            cy="555"
            r="18"
            fill="#ffffff"/>

    <circle cx="250"
            cy="555"
            r="18"
            fill="#ffffff"/>

    <circle cx="485"
            cy="520"
            r="18"
            fill="#ffffff"/>

    <circle cx="550"
            cy="520"
            r="18"
            fill="#ffffff"/>

    <text x="55"
          y="105"
          font-family="Arial"
          font-size="24"
          font-weight="700"
          fill="#6c5ce7">
        GINGAO MOCK PROVIDER
    </text>

    <text x="55"
          y="160"
          font-family="Arial"
          font-size="38"
          font-weight="800"
          fill="#17181b">
        {title}
    </text>

    <text x="55"
          y="1040"
          font-family="Arial"
          font-size="26"
          font-weight="800"
          fill="#17181b">
        ESCENA {scene.position}
    </text>

    <foreignObject x="55"
                   y="1080"
                   width="650"
                   height="180">

        <div xmlns="http://www.w3.org/1999/xhtml"
             style="
                font-family: Arial;
                font-size: 22px;
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
                category="mock",
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
                "/static/generated/mock/"
                + filename
            )

        return ImageResult(
            success=True,
            url=public_url,
            provider=self.code,
            external_cost_usd=0.0,
        )


class FalFluxTurboProvider(ImageProvider):

    code = "fal"
    display_name = "fal.ai / FLUX.2 Turbo"

    # Se activará después de validar economía.
    credit_cost = 0

    model_id = "fal-ai/flux-2/turbo"

    width = 768
    height = 1365

    def generate(self, *, prompt, project, scene):

        profile = get_generation_profile(
            project
        )

        width = profile["width"]
        height = profile["height"]

        fal_key = os.environ.get(
            "FAL_KEY",
            ""
        ).strip()

        if not fal_key:
            return ImageResult(
                success=False,
                provider=self.code,
                error=(
                    "FAL_KEY no esta configurada. "
                    "No se ha realizado ninguna solicitud."
                ),
            )

        try:
            import fal_client
        except ImportError:
            return ImageResult(
                success=False,
                provider=self.code,
                error=(
                    "fal-client no esta instalado. "
                    "Ejecuta: pip install fal-client"
                ),
            )

        try:

            result = fal_client.subscribe(
                self.model_id,
                arguments={
                    "prompt": prompt,
                    "image_size": {
                        "width": width,
                        "height": height,
                    },
                    "num_images": 1,
                },
            )

            images = result.get(
                "images",
                []
            )

            if not images:
                raise RuntimeError(
                    "fal.ai no devolvio imagenes."
                )

            remote_url = images[0].get(
                "url"
            )

            if not remote_url:
                raise RuntimeError(
                    "fal.ai devolvio una imagen sin URL."
                )

            output_dir = (
                Path(settings.BASE_DIR)
                / "static"
                / "generated"
                / "fal"
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
                f"{seed}.webp"
            )

            path = (
                output_dir
                / filename
            )

            request = urllib.request.Request(
                remote_url,
                headers={
                    "User-Agent": "Gingao/1.0"
                },
            )

            with urllib.request.urlopen(
                request,
                timeout=90
            ) as response:

                image_bytes = response.read()

            if _use_unified_storage():

                stored = save_generated_bytes(
                    category="fal",
                    filename=filename,
                    content=image_bytes,
                )

                public_url = stored["url"]

            else:

                path.write_bytes(
                    image_bytes
                )

                public_url = (
                    "/static/generated/fal/"
                    + filename
                )

            # Coste estimado segun los pixeles reales solicitados.
            # Precio publicado: $0.008 / MP.
            estimated_cost = (
                (
                    width
                    * height
                )
                / 1_000_000
            ) * 0.008

            return ImageResult(
                success=True,
                url=public_url,
                provider=self.code,
                external_cost_usd=estimated_cost,
            )

        except Exception as exc:

            return ImageResult(
                success=False,
                provider=self.code,
                error=str(exc),
            )


PROVIDERS = {
    "mock": MockImageProvider,
    "fal": FalFluxTurboProvider,
}


def get_image_provider(
    code=None
):

    code = (
        code
        or os.environ.get(
            "GINGAO_IMAGE_PROVIDER",
            "mock"
        )
    ).strip().lower()

    provider_class = PROVIDERS.get(
        code
    )

    if provider_class is None:
        raise ValueError(
            f"Proveedor desconocido: {code}"
        )

    return provider_class()
