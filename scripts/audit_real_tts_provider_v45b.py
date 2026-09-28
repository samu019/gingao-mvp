from pathlib import Path
import os
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

import django
django.setup()

from generations.audio_providers import (
    ElevenLabsAudioProvider,
    MockAudioProvider,
    get_audio_provider,
)


print()
print("=" * 104)
print("GINGAO V45B - REAL TTS PROVIDER AUDIT")
print("=" * 104)


# =============================================================================
# REGISTRY
# =============================================================================

mock = get_audio_provider(
    "mock"
)

real = get_audio_provider(
    "elevenlabs"
)


assert isinstance(
    mock,
    MockAudioProvider,
)

assert isinstance(
    real,
    ElevenLabsAudioProvider,
)


print(
    "MOCK AUDIO PROVIDER: OK"
)

print(
    "ELEVENLABS PROVIDER REGISTERED: OK"
)


# =============================================================================
# DEFAULT REMAINS MOCK
# =============================================================================

previous_provider = os.environ.get(
    "GINGAO_AUDIO_PROVIDER"
)

try:

    os.environ.pop(
        "GINGAO_AUDIO_PROVIDER",
        None,
    )

    default_provider = (
        get_audio_provider()
    )

    assert isinstance(
        default_provider,
        MockAudioProvider,
    )

finally:

    if previous_provider is not None:

        os.environ[
            "GINGAO_AUDIO_PROVIDER"
        ] = previous_provider


print(
    "DEFAULT AUDIO PROVIDER STILL MOCK: OK"
)


# =============================================================================
# NO API KEY -> NO NETWORK
# =============================================================================

old_key = os.environ.get(
    "ELEVENLABS_API_KEY"
)

old_voice = os.environ.get(
    "GINGAO_ELEVENLABS_VOICE_ID"
)


class DummyProject:
    id = 999999


try:

    os.environ.pop(
        "ELEVENLABS_API_KEY",
        None,
    )

    os.environ.pop(
        "GINGAO_ELEVENLABS_VOICE_ID",
        None,
    )


    result = real.generate(
        text="V45B safety test",
        project=DummyProject(),
        duration_seconds=5,
    )


    assert result.success is False
    assert result.provider == "elevenlabs"
    assert result.is_mock is False

    assert (
        "No se ha realizado"
        in result.error
    )

finally:

    if old_key is not None:

        os.environ[
            "ELEVENLABS_API_KEY"
        ] = old_key


    if old_voice is not None:

        os.environ[
            "GINGAO_ELEVENLABS_VOICE_ID"
        ] = old_voice


print(
    "NO API KEY -> NO REQUEST: OK"
)


# =============================================================================
# API KEY BUT NO VOICE -> STILL NO NETWORK
# =============================================================================

old_key = os.environ.get(
    "ELEVENLABS_API_KEY"
)

old_voice = os.environ.get(
    "GINGAO_ELEVENLABS_VOICE_ID"
)


try:

    os.environ[
        "ELEVENLABS_API_KEY"
    ] = "V45B_FAKE_KEY"

    os.environ.pop(
        "GINGAO_ELEVENLABS_VOICE_ID",
        None,
    )


    result = real.generate(
        text="V45B second safety test",
        project=DummyProject(),
        duration_seconds=5,
    )


    assert result.success is False

    assert (
        "VOICE_ID"
        in result.error
    )

finally:

    if old_key is None:
        os.environ.pop(
            "ELEVENLABS_API_KEY",
            None,
        )
    else:
        os.environ[
            "ELEVENLABS_API_KEY"
        ] = old_key


    if old_voice is None:
        os.environ.pop(
            "GINGAO_ELEVENLABS_VOICE_ID",
            None,
        )
    else:
        os.environ[
            "GINGAO_ELEVENLABS_VOICE_ID"
        ] = old_voice


print(
    "NO VOICE ID -> NO REQUEST: OK"
)


# =============================================================================
# CURRENT MOCK REALLY CREATES PHYSICAL WAV
# =============================================================================

class MockProject:
    id = 999998


mock_result = mock.generate(
    text="Physical WAV validation",
    project=MockProject(),
    duration_seconds=1,
)


assert mock_result.success is True
assert mock_result.url.endswith(
    ".wav"
)


prefix = (
    "/static/"
)

assert mock_result.url.startswith(
    prefix
)


physical = (
    ROOT
    / "static"
    / mock_result.url[
        len(prefix):
    ]
)


assert physical.exists()
assert physical.stat().st_size > 44


with wave.open(
    str(physical),
    "rb",
) as wav_file:

    assert wav_file.getnchannels() == 1
    assert wav_file.getframerate() == 16000
    assert wav_file.getnframes() > 0


print(
    "MOCK PHYSICAL WAV EXISTS: OK"
)

print(
    "MOCK WAV FORMAT VALID: OK"
)


try:
    physical.unlink()
except OSError:
    pass


# =============================================================================
# CONFIG
# =============================================================================

assert (
    real._model_id()
    or ""
)

assert (
    real._output_format()
    == "mp3_44100_128"
)


print(
    "DEFAULT MODEL CONFIG: OK"
)

print(
    "DEFAULT MP3 OUTPUT FORMAT: OK"
)


print()
print(
    "NO NETWORK REQUEST WAS EXECUTED"
)

print(
    "NO PAID TTS CALL WAS EXECUTED"
)

print()
print("=" * 104)
print("AUDIT_REAL_TTS_PROVIDER_V45B: OK")
print("=" * 104)
