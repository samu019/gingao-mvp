from pathlib import Path
import os
import sys

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

from generations.video_providers import (
    FalVideoProvider,
    MockVideoProvider,
    get_video_provider,
)


print()
print("=" * 100)
print("GINGAO V44B - REAL VIDEO PROVIDER AUDIT")
print("=" * 100)


# ============================================================
# REGISTRY
# ============================================================

mock = get_video_provider(
    "mock"
)

real = get_video_provider(
    "fal"
)

assert isinstance(
    mock,
    MockVideoProvider,
)

assert isinstance(
    real,
    FalVideoProvider,
)

print(
    "MOCK PROVIDER: OK"
)

print(
    "FAL PROVIDER REGISTERED: OK"
)


# ============================================================
# DEFAULT REMAINS MOCK
# ============================================================

previous_provider = os.environ.get(
    "GINGAO_VIDEO_PROVIDER"
)

try:

    os.environ.pop(
        "GINGAO_VIDEO_PROVIDER",
        None,
    )

    default_provider = (
        get_video_provider()
    )

    assert isinstance(
        default_provider,
        MockVideoProvider,
    )

finally:

    if previous_provider is not None:

        os.environ[
            "GINGAO_VIDEO_PROVIDER"
        ] = previous_provider


print(
    "DEFAULT PROVIDER STILL MOCK: OK"
)


# ============================================================
# NO-KEY SAFETY GATE
# ============================================================

previous_key = os.environ.get(
    "FAL_KEY"
)

try:

    os.environ.pop(
        "FAL_KEY",
        None,
    )


    class DummyProject:
        quality_tier = "standard"


    class DummyScene:
        duration_seconds = 5


    result = real.generate(
        prompt="V44B safety test",
        project=DummyProject(),
        scene=DummyScene(),
        image_url=(
            "/static/does-not-matter.png"
        ),
    )


    assert result.success is False

    assert result.provider == "fal"

    assert result.is_mock is False

    assert (
        "No se ha realizado"
        in result.error
    )

finally:

    if previous_key is not None:

        os.environ[
            "FAL_KEY"
        ] = previous_key


print(
    "NO FAL KEY -> NO REQUEST: OK"
)


# ============================================================
# PROFILE MAPPING
# ============================================================

class FastProject:
    quality_tier = "fast"


class StandardProject:
    quality_tier = "standard"


class PremiumProject:
    quality_tier = "premium"


assert (
    real._resolution_for_project(
        FastProject()
    )
    == "720p"
)

assert (
    real._resolution_for_project(
        StandardProject()
    )
    == "1080p"
)

assert (
    real._resolution_for_project(
        PremiumProject()
    )
    == "1080p"
)


print(
    "FAST -> 720P: OK"
)

print(
    "STANDARD -> 1080P: OK"
)

print(
    "PREMIUM SOURCE -> 1080P: OK"
)


# ============================================================
# DURATION CLAMP
# ============================================================

class ShortScene:
    duration_seconds = 1


class NormalScene:
    duration_seconds = 6


class LongScene:
    duration_seconds = 30


assert (
    real._duration_for_scene(
        ShortScene()
    )
    == 3
)

assert (
    real._duration_for_scene(
        NormalScene()
    )
    == 6
)

assert (
    real._duration_for_scene(
        LongScene()
    )
    == 15
)


print(
    "DURATION 3..15 CLAMP: OK"
)


# ============================================================
# COST ESTIMATE
# ============================================================

assert (
    real._external_cost_estimate(
        resolution="720p",
        duration=5,
        model_id=(
            real.default_model_id
        ),
    )
    == 0.70
)

assert (
    real._external_cost_estimate(
        resolution="1080p",
        duration=5,
        model_id=(
            real.default_model_id
        ),
    )
    == 1.40
)


print(
    "EXTERNAL COST ESTIMATE: OK"
)

print()
print(
    "NO PAID API CALL WAS EXECUTED"
)

print()
print("=" * 100)
print("AUDIT_REAL_VIDEO_PROVIDER_V44B: OK")
print("=" * 100)
