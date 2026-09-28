import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

import django
django.setup()

from django.contrib.auth import get_user_model

from credits.models import (
    CreditWallet,
    CreditTransaction,
)

from credits.services import grant_credits

from generations.services import (
    create_generation,
    mark_generation_failed,
)

from projects.models import Project


User = get_user_model()

username = "__gingao_validation__"

User.objects.filter(
    username=username
).delete()

user = User.objects.create_user(
    username=username,
    password="ValidationOnly123!",
    email="validation@gingao.local",
)

wallet = CreditWallet.objects.create(
    user=user,
    balance=0,
)

grant_credits(
    user,
    100,
    reference="phase2-validation",
)

wallet.refresh_from_db()

assert wallet.balance == 100

project = Project.objects.create(
    owner=user,
    title="Phase 2 validation",
    target_duration_seconds=15,
)

generation = create_generation(
    project=project,
    model_code="ltx-fast",
    resolution="720p",
    duration_seconds=3,
)

wallet.refresh_from_db()

assert generation.estimated_credits == 18
assert generation.status == "queued"
assert wallet.balance == 82

mark_generation_failed(
    generation,
    "intentional validation failure",
)

wallet.refresh_from_db()
generation.refresh_from_db()

assert generation.status == "failed"
assert wallet.balance == 100

assert CreditTransaction.objects.filter(
    wallet=wallet,
    kind="reserve",
).exists()

assert CreditTransaction.objects.filter(
    wallet=wallet,
    kind="refund",
).exists()

user.delete()

print("VALIDATE_CREDIT_FLOW: OK")
print("Grant: 100")
print("Reserve: 18")
print("Balance after reserve: 82")
print("Refund: 18")
print("Final balance: 100")
