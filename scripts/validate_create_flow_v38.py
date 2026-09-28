import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT)
    )

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

import django
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import Client

from projects.models import Project
from projects.creation_pricing import (
    calculate_creation_cost,
)
from projects.views import _wallet_for


print()
print("=" * 96)
print("GINGAO V38 - END TO END CREATE VALIDATION")
print("=" * 96)


User = get_user_model()

user = User.objects.get(
    username="Samuelmba"
)

wallet = _wallet_for(
    user
)

initial_balance = wallet.balance
initial_projects = Project.objects.filter(
    owner=user
).count()


print()
print("TEST CONFIGURATION")
print("-" * 96)

duration = 30
aspect_ratio = "16:9"
quality = "premium"
voice_enabled = False

expected_cost = calculate_creation_cost(
    duration=duration,
    quality=quality,
    voice_enabled=voice_enabled,
)

print("User:", user.username)
print("Duration:", duration)
print("Aspect ratio:", aspect_ratio)
print("Voice:", voice_enabled)
print("Quality:", quality)
print("Expected cost:", expected_cost)
print("Initial balance:", initial_balance)
print("Initial projects:", initial_projects)


assert expected_cost == 9, (
    f"Expected pricing test to equal 9, "
    f"got {expected_cost}"
)


client = Client(
    HTTP_HOST="127.0.0.1",
)

client.force_login(
    user
)


print()
print("=" * 96)
print("POST /create/")
print("=" * 96)


with transaction.atomic():

    response = client.post(
        "/create/",
        {
            "title":
                "V38 VALIDATION TEMP",
            "idea":
                (
                    "Proyecto temporal para validar "
                    "la configuracion de Gingao."
                ),
            "template_code":
                "fruit_story",
            "duration":
                str(duration),
            "aspect_ratio":
                aspect_ratio,
            "voice_enabled":
                "0",
            "quality_tier":
                quality,
        },
        follow=False,
        HTTP_HOST="127.0.0.1",
    )


    print(
        "HTTP status:",
        response.status_code,
    )


    if response.status_code not in (
        301,
        302,
    ):
        print()
        print(
            "ERROR: creation request did not redirect."
        )

        try:
            content = response.content.decode(
                "utf-8",
                errors="ignore",
            )

            print(
                content[:3000]
            )

        except Exception:
            pass

        raise AssertionError(
            "POST /create/ did not succeed."
        )


    project = (
        Project.objects
        .filter(
            owner=user,
            title="V38 VALIDATION TEMP",
        )
        .order_by("-id")
        .first()
    )


    assert project is not None, (
        "Project was not created."
    )


    wallet.refresh_from_db()

    current_balance = wallet.balance

    charged = (
        initial_balance
        - current_balance
    )


    print()
    print("=" * 96)
    print("PROJECT VALUES")
    print("=" * 96)

    print(
        "Project ID:",
        project.id,
    )

    print(
        "Duration:",
        project.target_duration_seconds,
    )

    print(
        "Aspect ratio:",
        project.aspect_ratio,
    )

    print(
        "Voice enabled:",
        project.voice_enabled,
    )

    print(
        "Quality tier:",
        project.quality_tier,
    )

    print(
        "Stored estimated cost:",
        project.estimated_credit_cost,
    )


    print()
    print("=" * 96)
    print("CREDIT VALIDATION")
    print("=" * 96)

    print(
        "Balance before:",
        initial_balance,
    )

    print(
        "Balance after temporary creation:",
        current_balance,
    )

    print(
        "Credits charged:",
        charged,
    )

    print(
        "Expected:",
        expected_cost,
    )


    assert (
        project.target_duration_seconds
        == duration
    ), (
        "Duration was not stored correctly."
    )

    assert (
        project.aspect_ratio
        == aspect_ratio
    ), (
        "Aspect ratio was not stored correctly."
    )

    assert (
        project.voice_enabled
        is voice_enabled
    ), (
        "Voice setting was not stored correctly."
    )

    assert (
        project.quality_tier
        == quality
    ), (
        "Quality tier was not stored correctly."
    )

    assert (
        project.estimated_credit_cost
        == expected_cost
    ), (
        "Stored project cost differs "
        "from backend calculation."
    )

    assert (
        charged
        == expected_cost
    ), (
        f"Wallet charged {charged}, "
        f"expected {expected_cost}."
    )


    scenes = list(
        project.scenes.all()
    )

    assert len(scenes) == 1, (
        "Initial project should contain "
        "exactly one temporary scene."
    )

    assert (
        scenes[0].duration_seconds
        == duration
    ), (
        "Initial scene duration does not "
        "match project duration."
    )


    print()
    print("PROJECT SETTINGS: OK")
    print("DURATION PERSISTENCE: OK")
    print("ASPECT RATIO PERSISTENCE: OK")
    print("VOICE PERSISTENCE: OK")
    print("QUALITY PERSISTENCE: OK")
    print("BACKEND COST CALCULATION: OK")
    print("WALLET CHARGE: OK")
    print("INITIAL SCENE: OK")


    # Important:
    # Roll back the complete test so no credits or
    # temporary project remain in the database.
    transaction.set_rollback(
        True
    )


# Reload from clean database after rollback.
wallet = _wallet_for(
    user
)

wallet.refresh_from_db()

final_balance = wallet.balance

final_projects = Project.objects.filter(
    owner=user
).count()


print()
print("=" * 96)
print("ROLLBACK VALIDATION")
print("=" * 96)

print(
    "Final balance:",
    final_balance,
)

print(
    "Final project count:",
    final_projects,
)


assert (
    final_balance
    == initial_balance
), (
    "Rollback failed: wallet balance changed."
)

assert (
    final_projects
    == initial_projects
), (
    "Rollback failed: temporary project remains."
)


print()
print("ROLLBACK: OK")
print("NO PERMANENT CREDIT CHARGE: OK")
print("NO TEMP PROJECT LEFT: OK")

print()
print("=" * 96)
print("AUDIT_CREATE_FLOW_V38: OK")
print("=" * 96)
