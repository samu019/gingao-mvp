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

import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generations.services import estimate_credits
cases=[('ltx-fast','720p',3,18),('ltx-fast','720p',5,30),('ltx-quality','720p',5,45)]
errors=[]
for m,r,d,e in cases:
    got=estimate_credits(m,r,d)
    if got!=e: errors.append((m,r,d,e,got))
print('VALIDATE_COSTS: OK' if not errors else f'VALIDATE_COSTS: FAIL {errors}')
raise SystemExit(1 if errors else 0)
