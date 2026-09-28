from django.db import connection

from config.runtime import (
    get_runtime_config,
)

from config.security import (
    security_warnings,
)


def database_ok():

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT 1"
            )

            value = cursor.fetchone()

        return bool(
            value
            and value[0] == 1
        )

    except Exception:
        return False


def get_health_snapshot():

    cfg = get_runtime_config()

    db_ok = database_ok()

    warnings = (
        security_warnings()
    )

    return {
        "status":
            "ok"
            if db_ok
            else "degraded",

        "database":
            "ok"
            if db_ok
            else "error",

        "mode":
            cfg.mode,

        "providers": {
            "image":
                cfg.image_provider,

            "video":
                cfg.video_provider,

            "audio":
                cfg.audio_provider,
        },

        "security_warning_count":
            len(warnings),
    }
