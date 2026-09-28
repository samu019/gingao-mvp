import os

from django.conf import settings


INSECURE_SECRET_FRAGMENTS = [
    "django-insecure",
    "change-me",
    "changeme",
    "secret-key",
]


def env_list(
    name,
):
    value = (
        os.environ
        .get(name, "")
        .strip()
    )

    if not value:
        return []

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def security_warnings():

    warnings = []

    mode = (
        os.environ
        .get(
            "GINGAO_MODE",
            "development"
        )
        .lower()
    )

    if mode != "production":
        warnings.append(
            "La aplicacion sigue en "
            "modo development."
        )

    if (
        mode == "production"
        and settings.DEBUG
    ):
        warnings.append(
            "DEBUG debe estar desactivado "
            "en produccion."
        )

    secret = str(
        settings.SECRET_KEY
    )

    if (
        len(secret) < 40
        or any(
            fragment in secret.lower()
            for fragment
            in INSECURE_SECRET_FRAGMENTS
        )
    ):
        warnings.append(
            "SECRET_KEY debe reemplazarse "
            "por un secreto fuerte."
        )

    if mode == "production":

        if not settings.ALLOWED_HOSTS:
            warnings.append(
                "ALLOWED_HOSTS esta vacio."
            )

        if "*" in settings.ALLOWED_HOSTS:
            warnings.append(
                "ALLOWED_HOSTS no debe usar "
                "'*' en produccion."
            )

        if not getattr(
            settings,
            "SESSION_COOKIE_SECURE",
            False
        ):
            warnings.append(
                "SESSION_COOKIE_SECURE "
                "debe estar activo."
            )

        if not getattr(
            settings,
            "CSRF_COOKIE_SECURE",
            False
        ):
            warnings.append(
                "CSRF_COOKIE_SECURE "
                "debe estar activo."
            )

        if not getattr(
            settings,
            "SECURE_SSL_REDIRECT",
            False
        ):
            warnings.append(
                "SECURE_SSL_REDIRECT "
                "debe estar activo."
            )

    return warnings


def security_ready():
    return not security_warnings()


def security_snapshot():

    mode = (
        os.environ
        .get(
            "GINGAO_MODE",
            "development"
        )
        .lower()
    )

    return {
        "mode": mode,

        "debug":
            settings.DEBUG,

        "allowed_hosts":
            list(
                settings.ALLOWED_HOSTS
            ),

        "session_cookie_secure":
            getattr(
                settings,
                "SESSION_COOKIE_SECURE",
                False
            ),

        "csrf_cookie_secure":
            getattr(
                settings,
                "CSRF_COOKIE_SECURE",
                False
            ),

        "ssl_redirect":
            getattr(
                settings,
                "SECURE_SSL_REDIRECT",
                False
            ),

        "hsts_seconds":
            getattr(
                settings,
                "SECURE_HSTS_SECONDS",
                0
            ),

        "media_root":
            str(
                settings.MEDIA_ROOT
            ),

        "warnings":
            security_warnings(),
    }
