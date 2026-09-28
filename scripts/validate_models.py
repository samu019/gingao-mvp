import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django; django.setup()
from django.apps import apps
expected={'accounts.User','credits.CreditWallet','credits.CreditTransaction','projects.Project','projects.Scene','assets_app.Asset','generations.VideoGeneration'}
actual={f'{m._meta.app_label}.{m.__name__}' for m in apps.get_models()}
missing=sorted(expected-actual)
print('VALIDATE_MODELS: OK' if not missing else f'VALIDATE_MODELS: MISSING {missing}')
raise SystemExit(1 if missing else 0)
