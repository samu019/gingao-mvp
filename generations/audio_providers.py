from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
import math
import os
import struct
import wave
import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from config.storage import save_generated_bytes



def _use_unified_storage():
    """
    V47 generated-file storage rollout.

    legacy:
        /static/generated/...

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
class AudioResult:
    success: bool
    url: str = ""
    provider: str = ""
    error: str = ""
    external_cost_usd: float = 0.0
    is_mock: bool = False
    duration_seconds: int = 0


class AudioProvider(ABC):

    code = "base"
    display_name = "Base Audio Provider"
    credit_cost = 0

    @abstractmethod
    def generate(
        self,
        *,
        text,
        project,
        duration_seconds,
    ):
        raise NotImplementedError


class MockAudioProvider(AudioProvider):

    code = "mock"
    display_name = "Mock Audio Provider"
    credit_cost = 0

    def generate(
        self,
        *,
        text,
        project,
        duration_seconds,
    ):
        duration_seconds = max(
            int(duration_seconds or 1),
            1
        )

        output_dir = (
            Path(settings.BASE_DIR)
            / "static"
            / "generated"
            / "audio_mock"
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        filename = (
            f"project_{project.id}_"
            f"{uuid4().hex[:12]}.wav"
        )

        destination = (
            output_dir
            / filename
        )

        sample_rate = 16000
        amplitude = 900
        frequency = 220.0

        total_frames = (
            sample_rate
            * duration_seconds
        )

        with wave.open(
            str(destination),
            "wb"
        ) as wav_file:

            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(
                sample_rate
            )

            frames = bytearray()

            for i in range(
                total_frames
            ):
                # Tono muy suave para verificar
                # que existe audio real.
                envelope = 0.10

                value = int(
                    amplitude
                    * envelope
                    * math.sin(
                        2.0
                        * math.pi
                        * frequency
                        * i
                        / sample_rate
                    )
                )

                frames.extend(
                    struct.pack(
                        "<h",
                        value
                    )
                )

            wav_file.writeframes(
                bytes(frames)
            )

        if _use_unified_storage():

            stored = save_generated_bytes(
                category="audio_mock",
                filename=filename,
                content=destination.read_bytes(),
            )

            public_url = stored["url"]

            try:
                destination.unlink()
            except OSError:
                pass

        else:

            public_url = (
                "/static/generated/audio_mock/"
                + filename
            )

        return AudioResult(
            success=True,
            url=public_url,
            provider=self.code,
            external_cost_usd=0.0,
            is_mock=True,
            duration_seconds=duration_seconds,
        )



# =============================================================================
# GINGAO_REAL_TTS_PROVIDER_V45B
# =============================================================================

class ElevenLabsAudioProvider(AudioProvider):

    code = "elevenlabs"
    display_name = "ElevenLabs TTS"

    # Gingao internal credit charging will be connected
    # separately after economic validation.
    credit_cost = 0

    default_model_id = (
        "eleven_multilingual_v2"
    )

    default_output_format = (
        "mp3_44100_128"
    )


    def _api_key(self):

        return (
            os.environ.get(
                "ELEVENLABS_API_KEY",
                ""
            )
            .strip()
        )


    def _voice_id(self):

        return (
            os.environ.get(
                "GINGAO_ELEVENLABS_VOICE_ID",
                ""
            )
            .strip()
        )


    def _model_id(self):

        return (
            os.environ.get(
                "GINGAO_ELEVENLABS_MODEL",
                self.default_model_id,
            )
            .strip()
            or self.default_model_id
        )


    def _output_format(self):

        return (
            os.environ.get(
                "GINGAO_ELEVENLABS_OUTPUT_FORMAT",
                self.default_output_format,
            )
            .strip()
            or self.default_output_format
        )


    def _timeout_seconds(self):

        raw = (
            os.environ.get(
                "GINGAO_ELEVENLABS_TIMEOUT",
                "120",
            )
            .strip()
        )

        try:
            value = int(
                raw
                or 120
            )

        except (
            TypeError,
            ValueError,
        ):
            value = 120

        return max(
            10,
            min(
                value,
                300,
            ),
        )


    def _destination(
        self,
        project,
    ):

        output_dir = (
            Path(
                settings.BASE_DIR
            )
            / "static"
            / "generated"
            / "audio_elevenlabs"
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            f"project_{project.id}_"
            f"{uuid4().hex[:12]}.mp3"
        )

        return (
            output_dir / filename,
            (
                "/static/generated/"
                "audio_elevenlabs/"
                + filename
            ),
        )


    def generate(
        self,
        *,
        text,
        project,
        duration_seconds,
    ):

        # ---------------------------------------------------------
        # DOUBLE SAFETY GATE
        # ---------------------------------------------------------
        #
        # No API key -> no request.
        # No voice id -> no request.
        #
        # Registration alone therefore cannot spend money.

        api_key = (
            self._api_key()
        )

        if not api_key:

            return AudioResult(
                success=False,
                provider=self.code,
                error=(
                    "ELEVENLABS_API_KEY no esta "
                    "configurada. No se ha realizado "
                    "ninguna solicitud de pago."
                ),
                external_cost_usd=0.0,
                is_mock=False,
                duration_seconds=0,
            )


        voice_id = (
            self._voice_id()
        )

        if not voice_id:

            return AudioResult(
                success=False,
                provider=self.code,
                error=(
                    "GINGAO_ELEVENLABS_VOICE_ID no "
                    "esta configurada. No se ha "
                    "realizado ninguna solicitud."
                ),
                external_cost_usd=0.0,
                is_mock=False,
                duration_seconds=0,
            )


        clean_text = str(
            text
            or ""
        ).strip()

        if not clean_text:

            return AudioResult(
                success=False,
                provider=self.code,
                error=(
                    "No hay texto para sintetizar."
                ),
                external_cost_usd=0.0,
                is_mock=False,
                duration_seconds=0,
            )


        model_id = (
            self._model_id()
        )

        output_format = (
            self._output_format()
        )


        endpoint = (
            "https://api.elevenlabs.io/"
            "v1/text-to-speech/"
            + urllib.parse.quote(
                voice_id,
                safe="",
            )
            + "?output_format="
            + urllib.parse.quote(
                output_format,
                safe="",
            )
        )


        payload = {
            "text":
                clean_text,

            "model_id":
                model_id,
        }


        request = urllib.request.Request(
            endpoint,
            data=json.dumps(
                payload
            ).encode(
                "utf-8"
            ),
            headers={
                "xi-api-key":
                    api_key,

                "Content-Type":
                    "application/json",

                "Accept":
                    "audio/mpeg",
            },
            method="POST",
        )


        destination = None


        try:

            with urllib.request.urlopen(
                request,
                timeout=(
                    self._timeout_seconds()
                ),
            ) as response:

                audio_bytes = (
                    response.read()
                )


            if not audio_bytes:

                raise RuntimeError(
                    "ElevenLabs devolvio "
                    "audio vacio."
                )


            if _use_unified_storage():

                filename = (
                    f"project_{project.id}_"
                    f"{uuid4().hex[:12]}.mp3"
                )

                stored = save_generated_bytes(
                    category="audio_elevenlabs",
                    filename=filename,
                    content=audio_bytes,
                )

                public_url = stored["url"]

            else:

                destination, public_url = (
                    self._destination(
                        project
                    )
                )

                destination.write_bytes(
                    audio_bytes
                )

                if (
                    not destination.exists()
                    or destination.stat().st_size
                    <= 0
                ):
                    raise RuntimeError(
                        "No se pudo guardar "
                        "el audio generado."
                    )


            try:
                duration = max(
                    int(
                        duration_seconds
                        or 0
                    ),
                    0,
                )

            except (
                TypeError,
                ValueError,
            ):
                duration = 0


            return AudioResult(
                success=True,
                url=public_url,
                provider=self.code,
                external_cost_usd=0.0,
                is_mock=False,
                duration_seconds=duration,
            )


        except urllib.error.HTTPError as exc:

            try:

                body = (
                    exc.read()
                    .decode(
                        "utf-8",
                        errors="ignore",
                    )
                )

            except Exception:
                body = ""


            return AudioResult(
                success=False,
                provider=self.code,
                error=(
                    "ElevenLabs HTTP "
                    + str(
                        exc.code
                    )
                    + (
                        ": "
                        + body[:500]
                        if body
                        else ""
                    )
                ),
                external_cost_usd=0.0,
                is_mock=False,
                duration_seconds=0,
            )


        except urllib.error.URLError as exc:

            return AudioResult(
                success=False,
                provider=self.code,
                error=(
                    "Error de red ElevenLabs: "
                    + str(exc)
                ),
                external_cost_usd=0.0,
                is_mock=False,
                duration_seconds=0,
            )


        except Exception as exc:

            if (
                destination is not None
                and destination.exists()
            ):
                try:
                    destination.unlink()
                except OSError:
                    pass


            return AudioResult(
                success=False,
                provider=self.code,
                error=(
                    "Error ElevenLabs: "
                    + str(exc)
                ),
                external_cost_usd=0.0,
                is_mock=False,
                duration_seconds=0,
            )



PROVIDERS = {
    "mock": MockAudioProvider,
    "elevenlabs": ElevenLabsAudioProvider,
}


def get_audio_provider(
    code=None
):
    code = (
        code
        or os.environ.get(
            "GINGAO_AUDIO_PROVIDER",
            "mock"
        )
    ).strip().lower()

    provider_class = (
        PROVIDERS.get(code)
    )

    if provider_class is None:
        raise ValueError(
            "Proveedor de audio "
            f"desconocido: {code}"
        )

    return provider_class()
