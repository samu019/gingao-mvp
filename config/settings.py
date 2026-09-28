import os
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qsl
BASE_DIR = Path(__file__).resolve().parent.parent


def _gingao_database_from_url(value):
    """
    Convert DATABASE_URL into Django PostgreSQL settings.

    Supported schemes:
    postgresql://
    postgres://
    """

    parsed = urlparse(value)

    if parsed.scheme not in {
        "postgres",
        "postgresql",
    }:
        raise RuntimeError(
            "DATABASE_URL must use "
            "postgresql:// or postgres://"
        )

    if not parsed.hostname:
        raise RuntimeError(
            "DATABASE_URL is missing host."
        )

    if not parsed.path or parsed.path == "/":
        raise RuntimeError(
            "DATABASE_URL is missing database name."
        )

    config = {
        "ENGINE":
            "django.db.backends.postgresql",

        "NAME":
            unquote(
                parsed.path.lstrip("/")
            ),

        "USER":
            unquote(
                parsed.username or ""
            ),

        "PASSWORD":
            unquote(
                parsed.password or ""
            ),

        "HOST":
            parsed.hostname,

        "PORT":
            str(
                parsed.port or 5432
            ),

        "CONN_MAX_AGE":
            int(
                os.getenv(
                    "GINGAO_DB_CONN_MAX_AGE",
                    "60",
                )
            ),

        "CONN_HEALTH_CHECKS":
            True,
    }

    query = dict(
        parse_qsl(
            parsed.query,
            keep_blank_values=False,
        )
    )

    options = {}

    for key in (
        "sslmode",
        "sslrootcert",
        "sslcert",
        "sslkey",
        "connect_timeout",
    ):

        if key in query:
            options[key] = query[key]

    if options:
        config["OPTIONS"] = options

    return config

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY','dev-only-change-me')
DEBUG = os.getenv('DJANGO_DEBUG','1') == '1'
ALLOWED_HOSTS = ['*'] if DEBUG else []
INSTALLED_APPS = [
    'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes',
    'django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
    'accounts','credits','projects','assets_app','generations',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware','django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware',
]
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,
'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS=[]
LANGUAGE_CODE='es'
TIME_ZONE='UTC'
USE_I18N=True
USE_TZ=True
STATIC_URL='static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL='/media/'
MEDIA_ROOT=BASE_DIR/'media'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
AUTH_USER_MODEL='accounts.User'
CELERY_BROKER_URL=os.getenv('REDIS_URL','redis://localhost:6379/0')
CELERY_RESULT_BACKEND=CELERY_BROKER_URL


STATICFILES_DIRS = [
    BASE_DIR / "static",
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"



# ============================================================
# GINGAO_PHASE13_SECURITY
# ============================================================

import os as _gingao_os


GINGAO_MODE = (
    _gingao_os.environ
    .get(
        "GINGAO_MODE",
        "development"
    )
    .strip()
    .lower()
)


# ============================================================
# GINGAO_V50C_PAYMENT_SECURITY
# ============================================================

GINGAO_PAYMENT_MODE = (
    _gingao_os.environ
    .get(
        "GINGAO_PAYMENT_MODE",
        (
            "mock"
            if GINGAO_MODE == "development"
            else "disabled"
        ),
    )
    .strip()
    .lower()
)

if GINGAO_PAYMENT_MODE not in {
    "disabled",
    "mock",
    "live",
}:
    raise RuntimeError(
        "GINGAO_PAYMENT_MODE must be "
        "'disabled', 'mock' or 'live'."
    )

# Mock payment endpoints must never be active in production.
if (
    GINGAO_MODE == "production"
    and GINGAO_PAYMENT_MODE == "mock"
):
    raise RuntimeError(
        "Mock payments are forbidden "
        "when GINGAO_MODE=production."
    )

GINGAO_PAYMENTS_LIVE = (
    GINGAO_PAYMENT_MODE == "live"
)

GINGAO_MOCK_PAYMENTS_ENABLED = (
    GINGAO_MODE == "development"
    and GINGAO_PAYMENT_MODE == "mock"
)



def _gingao_env_bool(
    name,
    default=False,
):
    raw = (
        _gingao_os.environ
        .get(
            name,
            "1"
            if default
            else "0"
        )
        .strip()
        .lower()
    )

    return raw in {
        "1",
        "true",
        "yes",
        "on",
    }


def _gingao_env_list(
    name,
    default="",
):
    raw = (
        _gingao_os.environ
        .get(
            name,
            default
        )
    )

    return [
        item.strip()
        for item in raw.split(",")
        if item.strip()
    ]


MEDIA_URL = "/media/"

MEDIA_ROOT = (
    BASE_DIR
    / "media"
)


# ---------------------------------------------------------------------
# GINGAO V47X - dual media storage
# ---------------------------------------------------------------------

GINGAO_STORAGE_BACKEND = (
    os.getenv(
        "GINGAO_STORAGE_BACKEND",
        (
            "s3"
            if GINGAO_MODE == "production"
            else "filesystem"
        ),
    )
    .strip()
    .lower()
)


if GINGAO_STORAGE_BACKEND not in {
    "filesystem",
    "s3",
}:

    raise RuntimeError(
        "GINGAO_STORAGE_BACKEND must be "
        "'filesystem' or 's3'."
    )


if GINGAO_STORAGE_BACKEND == "s3":

    GINGAO_S3_BUCKET_NAME = os.getenv(
        "GINGAO_S3_BUCKET_NAME",
        "",
    ).strip()

    GINGAO_S3_ACCESS_KEY_ID = os.getenv(
        "GINGAO_S3_ACCESS_KEY_ID",
        "",
    ).strip()

    GINGAO_S3_SECRET_ACCESS_KEY = os.getenv(
        "GINGAO_S3_SECRET_ACCESS_KEY",
        "",
    ).strip()

    GINGAO_S3_REGION_NAME = os.getenv(
        "GINGAO_S3_REGION_NAME",
        "",
    ).strip()

    GINGAO_S3_ENDPOINT_URL = os.getenv(
        "GINGAO_S3_ENDPOINT_URL",
        "",
    ).strip()

    GINGAO_S3_CUSTOM_DOMAIN = os.getenv(
        "GINGAO_S3_CUSTOM_DOMAIN",
        "",
    ).strip()


    missing_s3 = []

    if not GINGAO_S3_BUCKET_NAME:
        missing_s3.append(
            "GINGAO_S3_BUCKET_NAME"
        )

    if not GINGAO_S3_ACCESS_KEY_ID:
        missing_s3.append(
            "GINGAO_S3_ACCESS_KEY_ID"
        )

    if not GINGAO_S3_SECRET_ACCESS_KEY:
        missing_s3.append(
            "GINGAO_S3_SECRET_ACCESS_KEY"
        )


    if missing_s3:

        raise RuntimeError(
            "Missing required S3 settings: "
            + ", ".join(
                missing_s3
            )
        )


    s3_options = {
        "bucket_name":
            GINGAO_S3_BUCKET_NAME,

        "access_key":
            GINGAO_S3_ACCESS_KEY_ID,

        "secret_key":
            GINGAO_S3_SECRET_ACCESS_KEY,

        "default_acl":
            None,

        "file_overwrite":
            False,

        "querystring_auth":
            False,
    }


    if GINGAO_S3_REGION_NAME:

        s3_options[
            "region_name"
        ] = (
            GINGAO_S3_REGION_NAME
        )


    if GINGAO_S3_ENDPOINT_URL:

        s3_options[
            "endpoint_url"
        ] = (
            GINGAO_S3_ENDPOINT_URL
        )


    if GINGAO_S3_CUSTOM_DOMAIN:

        s3_options[
            "custom_domain"
        ] = (
            GINGAO_S3_CUSTOM_DOMAIN
        )


    STORAGES = {

        "default": {
            "BACKEND":
                "storages.backends.s3."
                "S3Storage",

            "OPTIONS":
                s3_options,
        },

        "staticfiles": {
            "BACKEND":
                "django.contrib.staticfiles."
                "storage.StaticFilesStorage",
        },
    }


else:

    STORAGES = {

        "default": {
            "BACKEND":
                "django.core.files.storage."
                "FileSystemStorage",

            "OPTIONS": {
                "location":
                    MEDIA_ROOT,

                "base_url":
                    MEDIA_URL,
            },
        },

        "staticfiles": {
            "BACKEND":
                "django.contrib.staticfiles."
                "storage.StaticFilesStorage",
        },
    }



if GINGAO_MODE == "production":

    # -----------------------------------------------------------------
    # GINGAO V48B - production Redis contract
    # -----------------------------------------------------------------

    GINGAO_REDIS_URL = os.getenv(
        "REDIS_URL",
        "",
    ).strip()

    if not GINGAO_REDIS_URL:

        raise RuntimeError(
            "REDIS_URL is required "
            "when GINGAO_MODE=production."
        )

    CELERY_BROKER_URL = (
        GINGAO_REDIS_URL
    )

    CELERY_RESULT_BACKEND = (
        GINGAO_REDIS_URL
    )

    # GINGAO V47E - PostgreSQL production database
    GINGAO_DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "",
    ).strip()

    if not GINGAO_DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is required "
            "when GINGAO_MODE=production."
        )

    DATABASES = {
        "default":
            _gingao_database_from_url(
                GINGAO_DATABASE_URL
            )
    }


    DEBUG = False

    ALLOWED_HOSTS = (
        _gingao_env_list(
            "GINGAO_ALLOWED_HOSTS"
        )
    )

    CSRF_TRUSTED_ORIGINS = (
        _gingao_env_list(
            "GINGAO_CSRF_TRUSTED_ORIGINS"
        )
    )

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"

    SECURE_SSL_REDIRECT = (
        _gingao_env_bool(
            "GINGAO_SECURE_SSL_REDIRECT",
            True
        )
    )

    SECURE_HSTS_SECONDS = int(
        _gingao_os.environ.get(
            "GINGAO_HSTS_SECONDS",
            "3600"
        )
    )

    SECURE_HSTS_INCLUDE_SUBDOMAINS = (
        _gingao_env_bool(
            "GINGAO_HSTS_INCLUDE_SUBDOMAINS",
            False
        )
    )

    SECURE_HSTS_PRELOAD = (
        _gingao_env_bool(
            "GINGAO_HSTS_PRELOAD",
            False
        )
    )

    SECURE_CONTENT_TYPE_NOSNIFF = True

    SECURE_REFERRER_POLICY = (
        "strict-origin-when-cross-origin"
    )

    X_FRAME_OPTIONS = "DENY"

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

else:

    # Safe localhost defaults.
    ALLOWED_HOSTS = list(
        set(
            list(ALLOWED_HOSTS)
            + [
                "127.0.0.1",
                "localhost",
            ]
        )
    )

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"

    CSRF_COOKIE_SAMESITE = "Lax"

    SECURE_CONTENT_TYPE_NOSNIFF = True

    X_FRAME_OPTIONS = "DENY"




# ---------------------------------------------------------------------
# GINGAO V47Z - production static storage
# ---------------------------------------------------------------------

if GINGAO_MODE == "production":

    STORAGES[
        "staticfiles"
    ] = {
        "BACKEND":
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
    }


# ---------------------------------------------------------------------
# GINGAO V47C - Production-safe console logging
# ---------------------------------------------------------------------

GINGAO_LOG_LEVEL = os.getenv(
    "GINGAO_LOG_LEVEL",
    "INFO",
).upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "gingao": {
            "format": (
                "%(asctime)s "
                "%(levelname)s "
                "%(name)s "
                "%(message)s"
            ),
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "gingao",
        },
    },

    "root": {
        "handlers": [
            "console",
        ],
        "level": GINGAO_LOG_LEVEL,
    },

    "loggers": {
        "django": {
            "handlers": [
                "console",
            ],
            "level": GINGAO_LOG_LEVEL,
            "propagate": False,
        },

        "gingao": {
            "handlers": [
                "console",
            ],
            "level": GINGAO_LOG_LEVEL,
            "propagate": False,
        },
    },
}



# ============================================================
# GINGAO_V50D_NOWPAYMENTS
# ============================================================

NOWPAYMENTS_API_BASE_URL = (
    _gingao_os.environ
    .get(
        "NOWPAYMENTS_API_BASE_URL",
        "https://api.nowpayments.io/v1",
    )
    .strip()
    .rstrip("/")
)

NOWPAYMENTS_API_KEY = (
    _gingao_os.environ
    .get(
        "NOWPAYMENTS_API_KEY",
        "",
    )
    .strip()
)

NOWPAYMENTS_IPN_SECRET = (
    _gingao_os.environ
    .get(
        "NOWPAYMENTS_IPN_SECRET",
        "",
    )
    .strip()
)

NOWPAYMENTS_USDT_CURRENCY = (
    _gingao_os.environ
    .get(
        "NOWPAYMENTS_USDT_CURRENCY",
        "usdttrc20",
    )
    .strip()
    .lower()
)

NOWPAYMENTS_TIMEOUT_SECONDS = int(
    _gingao_os.environ.get(
        "NOWPAYMENTS_TIMEOUT_SECONDS",
        "20",
    )
)

NOWPAYMENTS_PROVIDER_CODE = "nowpayments"



# ============================================================
# GINGAO_V50D4_PUBLIC_PAYMENT_URL
# ============================================================

GINGAO_PUBLIC_BASE_URL = (
    _gingao_os.environ
    .get(
        "GINGAO_PUBLIC_BASE_URL",
        "",
    )
    .strip()
    .rstrip("/")
)

