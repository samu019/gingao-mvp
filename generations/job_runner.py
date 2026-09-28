import inspect

from generations.models import (
    GenerationJob,
)

from generations.job_services import (
    mark_completed,
    mark_failed,
    mark_processing,
)


def _result_url(
    result,
    default="",
):
    if result is None:
        return default

    if isinstance(
        result,
        dict
    ):
        for key in [
            "url",
            "image_url",
            "video_url",
            "output_url",
            "file_url",
        ]:
            value = result.get(
                key
            )

            if value:
                return value

        return default

    for name in [
        "url",
        "image_url",
        "video_url",
        "output_url",
        "file_url",
    ]:
        value = getattr(
            result,
            name,
            None
        )

        if value:
            return value

    return default


def _invoke_compatible(
    function,
    *,
    job,
):
    """
    Calls an existing Gingao service while
    respecting its real Python signature.

    This avoids coupling the queue to one
    historical function name/signature.
    """

    signature = inspect.signature(
        function
    )

    available = {
        "project":
            job.project,

        "scene":
            job.scene,

        "user":
            job.user,

        "provider_code":
            job.provider,

        "provider":
            job.provider,

        "storyboard":
            (
                getattr(
                    job.scene,
                    "storyboard_image",
                    None
                )
                if job.scene
                else None
            ),

        "storyboard_image":
            (
                getattr(
                    job.scene,
                    "storyboard_image",
                    None
                )
                if job.scene
                else None
            ),
    }

    kwargs = {}

    missing = []

    for name, parameter in (
        signature.parameters.items()
    ):

        if name in available:

            value = available[
                name
            ]

            if value is not None:
                kwargs[name] = value
                continue

        if (
            parameter.default
            is not inspect.Parameter.empty
        ):
            continue

        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        missing.append(
            name
        )

    if missing:
        raise TypeError(
            f"{function.__name__} requiere "
            "parametros no disponibles: "
            + ", ".join(missing)
        )

    return function(
        **kwargs
    )


def _scene_storyboard_url(
    scene
):
    if scene is None:
        return ""

    try:
        storyboard = (
            scene.storyboard_image
        )
    except Exception:
        return ""

    return (
        getattr(
            storyboard,
            "image_url",
            ""
        )
        or ""
    )


def _run_image_job(
    job
):
    """
    Prefer a scene-level image function if
    the installed Gingao service exposes one.

    Fall back to the already validated bulk
    service if this project's image service
    only exposes bulk generation.
    """

    from generations import (
        image_services,
    )

    preferred_names = [
        "generate_scene_image",
        "generate_storyboard_image",
        "generate_image_for_scene",
        "generate_scene_storyboard",
        "generate_single_storyboard_image",
    ]

    for name in preferred_names:

        function = getattr(
            image_services,
            name,
            None
        )

        if callable(function):

            try:
                result = (
                    _invoke_compatible(
                        function,
                        job=job,
                    )
                )

                url = _result_url(
                    result
                )

                if not url:
                    url = (
                        _scene_storyboard_url(
                            job.scene
                        )
                    )

                if url:
                    return url

            except TypeError:
                # Try the next compatible
                # scene-level implementation.
                continue

    # Safe compatibility fallback.
    #
    # This service already existed and was
    # validated during the previous Gingao
    # image phases.
    bulk = getattr(
        image_services,
        "generate_all_storyboard_images",
        None
    )

    if not callable(bulk):
        raise RuntimeError(
            "No existe un generador de "
            "imagenes compatible en "
            "generations.image_services."
        )

    result = _invoke_compatible(
        bulk,
        job=job,
    )

    if job.scene is not None:
        job.scene.refresh_from_db()

    url = _scene_storyboard_url(
        job.scene
    )

    if not url:
        url = _result_url(
            result
        )

    if not url:
        raise RuntimeError(
            "El proveedor termino pero "
            "no devolvio image_url."
        )

    return url


def _run_video_job(
    job
):
    from generations import (
        video_services,
    )

    preferred_names = [
        "generate_scene_video",
        "generate_video_for_scene",
        "generate_single_scene_video",
    ]

    for name in preferred_names:

        function = getattr(
            video_services,
            name,
            None
        )

        if not callable(function):
            continue

        try:
            result = (
                _invoke_compatible(
                    function,
                    job=job,
                )
            )

            url = _result_url(
                result
            )

            if url:
                return url

        except TypeError:
            continue

    raise RuntimeError(
        "No existe un generador de "
        "video por escena compatible."
    )


def _run_audio_job(
    job
):
    from generations.audio_services import (
        generate_project_audio,
    )

    result = generate_project_audio(
        project=job.project,
        user=job.user,
        provider_code=job.provider,
    )

    url = _result_url(
        result
    )

    if not url:
        raise RuntimeError(
            "Audio generado sin URL."
        )

    return url


def _run_final_job(
    job
):
    from generations.final_services import (
        create_mock_final_cut,
    )

    result = create_mock_final_cut(
        project=job.project,
        user=job.user,
    )

    url = _result_url(
        result
    )

    if not url:
        raise RuntimeError(
            "Corte final creado sin URL."
        )

    return url


def execute_job(
    job,
):
    job = mark_processing(
        job.id
    )

    try:

        if job.job_type == (
            GenerationJob.TYPE_IMAGE
        ):

            result_url = (
                _run_image_job(
                    job
                )
            )

        elif job.job_type == (
            GenerationJob.TYPE_VIDEO
        ):

            result_url = (
                _run_video_job(
                    job
                )
            )

        elif job.job_type == (
            GenerationJob.TYPE_AUDIO
        ):

            result_url = (
                _run_audio_job(
                    job
                )
            )

        elif job.job_type == (
            GenerationJob.TYPE_FINAL
        ):

            result_url = (
                _run_final_job(
                    job
                )
            )

        else:

            raise RuntimeError(
                "Tipo de job desconocido."
            )

        return mark_completed(
            job_id=job.id,
            result_url=result_url,
        )

    except Exception as exc:

        mark_failed(
            job_id=job.id,
            error_message=exc,
        )

        raise
