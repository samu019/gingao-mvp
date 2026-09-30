from pathlib import Path
import os
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
)
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from assets_app.models import Asset
from credits.models import CreditWallet
from generations.models import VideoGeneration

from .models import Project
from .services import generate_project_script


User = get_user_model()


def _wallet_for(user):
    wallet, _ = CreditWallet.objects.get_or_create(
        user=user
    )
    return wallet


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)
            return redirect("home")

        messages.error(
            request,
            "Usuario o contrase\u00f1a incorrectos."
        )

    return render(
        request,
        "auth/login.html"
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        if len(username) < 3:
            messages.error(
                request,
                "El nombre de usuario debe tener "
                "al menos 3 caracteres."
            )

        elif len(password) < 8:
            messages.error(
                request,
                "La contrase\u00f1a debe tener "
                "al menos 8 caracteres."
            )

        elif User.objects.filter(
            username=username
        ).exists():
            messages.error(
                request,
                "Ese nombre de usuario ya existe."
            )

        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )

            CreditWallet.objects.create(
                user=user,
                balance=100,
            )

            login(request, user)

            messages.success(
                request,
                "Cuenta creada. Te hemos dado "
                "100 cr\u00e9ditos de prueba."
            )

            return redirect("home")

    return render(
        request,
        "auth/register.html"
    )


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def home(request):
    wallet = _wallet_for(request.user)

    recent_projects = (
        Project.objects
        .filter(owner=request.user)
        .order_by("-updated_at")[:4]
    )

    return render(
        request,
        "dashboard/home.html",
        {
            "wallet": wallet,
            "recent_projects": recent_projects,
            "project_count":
                Project.objects.filter(
                    owner=request.user
                ).count(),
            "asset_count":
                Asset.objects.filter(
                    owner=request.user
                ).count(),
            "generation_count":
                VideoGeneration.objects.filter(
                    project__owner=request.user
                ).count(),
        }
    )


@login_required
def projects_page(request):
    wallet = _wallet_for(request.user)

    projects = (
        Project.objects
        .filter(owner=request.user)
        .order_by("-updated_at")
    )

    return render(
        request,
        "dashboard/projects.html",
        {
            "wallet": wallet,
            "projects": projects,
        }
    )


@login_required
def assets_page(request):
    wallet = _wallet_for(request.user)

    assets = (
        Asset.objects
        .filter(owner=request.user)
        .order_by("-created_at")
    )

    return render(
        request,
        "dashboard/assets.html",
        {
            "wallet": wallet,
            "assets": assets,
        }
    )


@login_required
def profile_page(request):
    wallet = _wallet_for(request.user)

    transactions = (
        wallet.transactions
        .all()
        .order_by("-created_at")[:10]
    )

    return render(
        request,
        "dashboard/profile.html",
        {
            "wallet": wallet,
            "transactions": transactions,
        }
    )


@login_required
def create_video(request):
    wallet = _wallet_for(
        request.user
    )

    template_code = request.GET.get(
        "template",
        "fruit_story"
    )

    if request.method == "POST":

        from django.db import transaction

        from .creation_pricing import (
            normalize_creation_options,
        )

        title = (
            request.POST.get(
                "title",
                ""
            ).strip()
            or "Proyecto sin titulo"
        )

        idea = request.POST.get(
            "idea",
            ""
        ).strip()

        template_code = request.POST.get(
            "template_code",
            "fruit_story"
        )

        raw_duration = request.POST.get(
            "duration",
            "20"
        )

        aspect_ratio = request.POST.get(
            "aspect_ratio",
            "9:16"
        )

        quality = request.POST.get(
            "quality_tier",
            "standard"
        )

        voice_enabled = (
            request.POST.get(
                "voice_enabled",
                "1"
            )
            == "1"
        )

        # GINGAO_VOICE_SELECTION_V49B
        from generations.voice_catalog import (
            normalize_voice_preset,
        )

        voice_preset = normalize_voice_preset(
            request.POST.get(
                "voice_preset",
                "warm_female"
            )
        )

        options = (
            normalize_creation_options(
                duration=raw_duration,
                aspect_ratio=aspect_ratio,
                quality=quality,
                voice_enabled=voice_enabled,
            )
        )

        # GINGAO_CREATION_ESTIMATE_NO_CHARGE_V50A
        #
        # Project creation stores only an estimate.
        # Credits are charged when real generation happens.
        with transaction.atomic():

            project = (
                Project.objects.create(
                    owner=request.user,
                    title=title,
                    template_code=template_code,
                    status="draft",
                    target_duration_seconds=(
                        options[
                            "duration"
                        ]
                    ),
                    aspect_ratio=(
                        options[
                            "aspect_ratio"
                        ]
                    ),
                    voice_enabled=(
                        options[
                            "voice_enabled"
                        ]
                    ),
                    voice_preset=voice_preset,
                    quality_tier=(
                        options[
                            "quality"
                        ]
                    ),
                    estimated_credit_cost=(
                        options[
                            "cost"
                        ]
                    ),
                )
            )

            project.scenes.create(
                position=1,
                script=idea,
                duration_seconds=(
                    options[
                        "duration"
                    ]
                ),
            )

        messages.success(
            request,
            (
                "Proyecto creado. "
                f"Coste estimado: "
                f"{options['cost']} "
                "creditos. "
                "Los creditos se descontaran "
                "al generar contenido."
            )
        )

        return redirect(
            "project_workspace",
            project.id
        )

    return render(
        request,
        "dashboard/create_video.html",
        {
            "wallet":
                wallet,
            "template_code":
                template_code,
        }
    )

@login_required
def generate_script_view(request, project_id):
    if request.method != "POST":
        return redirect(
            "project_workspace",
            project_id
        )

    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    first_scene = project.scenes.first()

    idea = (
        first_scene.script
        if first_scene
        else project.title
    )

    scenes = generate_project_script(
        project,
        idea
    )

    messages.success(
        request,
        f"Gui\u00f3n generado: {len(scenes)} escenas."
    )

    return redirect(
        "project_workspace",
        project.id
    )


@login_required
def project_workspace(request, project_id):
    wallet = _wallet_for(request.user)

    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    scenes = project.scenes.all()

    generations = (
        project.generations
        .all()
        .order_by("-created_at")
    )

    return render(
        request,
        "dashboard/workspace.html",
        {
            "wallet": wallet,
            "project": project,
            "scenes": scenes,
            "generations": generations,
        }
    )


@login_required
def images_workspace(request, project_id):
    wallet = _wallet_for(request.user)

    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    from .image_services import (
        prepare_characters,
        prepare_storyboard,
    )

    if not project.characters.exists():
        prepare_characters(project)

    if not all(
        hasattr(scene, "storyboard_image")
        for scene in project.scenes.all()
    ):
        prepare_storyboard(project)

    scenes = list(
        project.scenes
        .select_related(
            "storyboard_image"
        )
        .order_by(
            "position"
        )
    )

    real_image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
    }

    real_scene_count = 0
    pending_scene_positions = []

    for scene in scenes:

        try:
            image_url = (
                scene.storyboard_image.image_url
                or ""
            )
        except Exception:
            image_url = ""

        suffix = Path(
            str(image_url).split("?")[0]
        ).suffix.lower()

        if (
            image_url
            and suffix
            in real_image_extensions
        ):
            real_scene_count += 1

        else:
            pending_scene_positions.append(
                scene.position
            )

    return render(
        request,
        "dashboard/images_workspace.html",
        {
            "wallet": wallet,
            "project": project,
            "characters":
                project.characters.all(),
            "scenes":
                scenes,
            "image_provider_code":
                os.environ.get(
                    "GINGAO_IMAGE_PROVIDER",
                    "mock"
                ).lower(),
            "real_scene_count":
                real_scene_count,
            "pending_scene_count":
                len(
                    pending_scene_positions
                ),
            "pending_scene_positions":
                pending_scene_positions,
        }
    )


@login_required
def prepare_images_view(request, project_id):
    if request.method != "POST":
        return redirect(
            "images_workspace",
            project_id
        )

    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    from .image_services import (
        prepare_characters,
        prepare_storyboard,
    )

    characters = prepare_characters(project)
    storyboard = prepare_storyboard(project)

    messages.success(
        request,
        f"Preparados {len(characters)} personajes "
        f"y {len(storyboard)} imagenes de storyboard."
    )

    return redirect(
        "images_workspace",
        project.id
    )



# =============================================================================
# GINGAO_IMAGE_GENERATION_GUARD_V48A
# =============================================================================

@login_required
def generate_scene_image_view(
    request,
    project_id,
    scene_id,
):
    if request.method != "POST":
        return redirect(
            "images_workspace",
            project_id
        )

    from django.db import transaction

    from projects.models import (
        Scene,
        StoryboardImage,
    )

    from generations.models import (
        GenerationJob,
    )

    from generations.image_services import (
        generate_storyboard_image,
    )

    from generations.job_services import (
        create_job,
        mark_processing,
        mark_completed,
        mark_failed,
    )

    from generations.pricing import (
        estimate_image_cost,
    )

    from credits.services import (
        reserve_credits,
        refund_credits,
        InsufficientCredits,
    )

    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    provider_code = os.environ.get(
        "GINGAO_IMAGE_PROVIDER",
        "mock",
    ).strip().lower()

    reserved_credits = 0
    job = None

    try:

        # --------------------------------------------------------------
        # Serialize requests for the SAME scene.
        # Prevents duplicate paid image generation.
        # --------------------------------------------------------------
        with transaction.atomic():

            scene = (
                Scene.objects
                .select_for_update()
                .get(
                    id=scene_id,
                    project=project,
                )
            )

            storyboard = (
                StoryboardImage.objects
                .select_related(
                    "scene",
                    "scene__project",
                )
                .get(
                    scene=scene,
                )
            )

            job, created = create_job(
                user=request.user,
                project=project,
                scene=scene,
                job_type=GenerationJob.TYPE_IMAGE,
                provider=provider_code,
                payload={
                    "scene_id": scene.id,
                    "storyboard_id": storyboard.id,
                },
            )

        if not created:

            messages.warning(
                request,
                (
                    f"La imagen de la escena "
                    f"{scene.position} ya se esta generando. "
                    "No se envio una segunda solicitud."
                )
            )

            return redirect(
                "images_workspace",
                project.id
            )

        estimate = estimate_image_cost()

        reserved_credits = int(
            estimate.internal_credits or 0
        )

        if reserved_credits > 0:

            reserve_credits(
                request.user,
                reserved_credits,
                reference=(
                    f"image-generation:{job.id}"
                ),
            )

        mark_processing(
            job.id
        )

        try:

            result = generate_storyboard_image(
                storyboard=storyboard,
                user=request.user,
                provider_code=provider_code,
            )

            storyboard.refresh_from_db()

            result_url = (
                storyboard.image_url or ""
            )

            if not result_url:
                raise RuntimeError(
                    "El proveedor termino sin URL de imagen."
                )

            mark_completed(
                job_id=job.id,
                result_url=result_url,
            )

        except Exception as exc:

            mark_failed(
                job_id=job.id,
                error_message=str(exc),
            )

            if reserved_credits > 0:

                refund_credits(
                    request.user,
                    reserved_credits,
                    reference=(
                        f"refund:image-generation:{job.id}"
                    ),
                )

            raise

        if result["asset"] is None:

            messages.warning(
                request,
                (
                    "Imagen generada correctamente, "
                    "pero no pudo registrarse "
                    "automaticamente en Mis activos."
                )
            )

        else:

            if provider_code == "fal":

                messages.success(
                    request,
                    (
                        f"Imagen IA de la escena "
                        f"{scene.position} generada "
                        "y guardada correctamente."
                    )
                )

            else:

                messages.success(
                    request,
                    (
                        f"Imagen Mock de la escena "
                        f"{scene.position} generada "
                        "y guardada correctamente."
                    )
                )

    except InsufficientCredits as exc:

        if job is not None:

            mark_failed(
                job_id=job.id,
                error_message=str(exc),
            )

        messages.error(
            request,
            str(exc),
        )

    except Scene.DoesNotExist:

        messages.error(
            request,
            "La escena solicitada no existe."
        )

    except StoryboardImage.DoesNotExist:

        messages.error(
            request,
            "La escena no tiene storyboard preparado."
        )

    except Exception as exc:

        messages.error(
            request,
            f"Error generando imagen: {exc}"
        )

    return redirect(
        "images_workspace",
        project.id
    )


@login_required
def generate_all_images_view(
    request,
    project_id,
):
    if request.method != "POST":
        return redirect(
            "images_workspace",
            project_id
        )

    from generations.image_services import (
        generate_all_storyboard_images,
    )

    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    try:
        provider_code = os.environ.get(
            "GINGAO_IMAGE_PROVIDER",
            "mock"
        ).lower()

        if (
            provider_code == "fal"
            and os.environ.get(
                "GINGAO_ALLOW_REAL_BULK",
                "0"
            ) != "1"
        ):
            messages.warning(
                request,
                "Generacion masiva real bloqueada por seguridad. "
                "Prueba primero una sola escena."
            )

            return redirect(
                "images_workspace",
                project.id
            )

        results = generate_all_storyboard_images(
            project=project,
            user=request.user,
            provider_code=provider_code,
        )

        assets_created = sum(
            1
            for result in results
            if result["asset"] is not None
        )

        messages.success(
            request,
            f"{len(results)} imagenes Mock generadas. "
            f"{assets_created} registradas en Mis activos."
        )

    except Exception as exc:
        messages.error(
            request,
            f"Error generando storyboard: {exc}"
        )

    return redirect(
        "images_workspace",
        project.id
    )



@login_required
def videos_workspace(
    request,
    project_id,
):
    wallet = _wallet_for(
        request.user
    )

    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    scenes = (
        project.scenes
        .all()
        .order_by("position")
    )

    from generations.models import (
        VideoGeneration,
    )

    generation_fields = {
        field.name
        for field in
        VideoGeneration._meta.fields
    }

    scene_videos = {}

    if "scene" in generation_fields:

        for generation in (
            VideoGeneration.objects
            .filter(
                scene__project=project
            )
            .order_by(
                "scene_id",
                "-pk",
            )
        ):

            if generation.scene_id not in scene_videos:

                url = ""

                for field_name in [
                    "output_url",
                    "video_url",
                    "url",
                    "file_url",
                ]:
                    if hasattr(
                        generation,
                        field_name
                    ):
                        value = getattr(
                            generation,
                            field_name
                        )

                        if value:
                            url = value
                            break

                clean_url = (
                    str(url)
                    .lower()
                    .split("?", 1)[0]
                )

                is_real_video = (
                    clean_url.endswith(
                        (
                            ".mp4",
                            ".webm",
                            ".mov",
                            ".m4v",
                        )
                    )
                )

                scene_videos[
                    generation.scene_id
                ] = {
                    "generation":
                        generation,
                    "url":
                        url,
                    "is_real_video":
                        is_real_video,
                }

    return render(
        request,
        "dashboard/videos_workspace.html",
        {
            "wallet": wallet,
            "project": project,
            "scenes": scenes,
            "scene_videos": scene_videos,
            "video_provider_code":
                os.environ.get(
                    "GINGAO_VIDEO_PROVIDER",
                    "mock"
                ).lower(),
        }
    )


# =============================================================================
# GINGAO_VIDEO_SYNC_FALLBACK_V47B
# =============================================================================

@login_required
def generate_scene_video_view(
    request,
    project_id,
    scene_id,
):
    if request.method != "POST":

        return redirect(
            "videos_workspace",
            project_id
        )

    from django.db import transaction

    from generations.models import (
        GenerationJob,
    )

    from projects.models import (
        Scene,
    )

    from generations.job_services import (
        create_job,
        mark_processing,
        mark_completed,
        mark_failed,
    )

    from generations.video_services import (
        generate_scene_video,
    )

    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    provider_code = os.environ.get(
        "GINGAO_VIDEO_PROVIDER",
        "mock"
    ).lower()

    try:

        # --------------------------------------------------------------
        # Serialize requests for the SAME scene.
        # Only one active video job may exist at a time.
        # --------------------------------------------------------------
        with transaction.atomic():

            scene = (
                Scene.objects
                .select_for_update()
                .get(
                    id=scene_id,
                    project=project,
                )
            )

            job, created = create_job(
                user=request.user,
                project=project,
                scene=scene,
                job_type=GenerationJob.TYPE_VIDEO,
                provider=provider_code,
                payload={
                    "scene_id": scene.id,
                },
            )

        if not created:

            messages.warning(
                request,
                (
                    f"La escena {scene.position} "
                    "ya se esta generando. "
                    "No se envio una segunda solicitud."
                )
            )

            return redirect(
                "videos_workspace",
                project.id
            )

        # --------------------------------------------------------------
        # Render Free currently has no Celery worker.
        # Execute synchronously while preserving GenerationJob state.
        # --------------------------------------------------------------
        mark_processing(
            job.id
        )

        try:

            result = generate_scene_video(
                scene=scene,
                user=request.user,
                provider_code=provider_code,
            )

            result_url = (
                result.get("url", "")
                if isinstance(result, dict)
                else ""
            )

            if not result_url:
                raise RuntimeError(
                    "El proveedor termino sin URL de video."
                )

            mark_completed(
                job_id=job.id,
                result_url=result_url,
            )

        except Exception as exc:

            mark_failed(
                job_id=job.id,
                error_message=str(exc),
            )

            raise

        messages.success(
            request,
            (
                f"Video de la escena "
                f"{scene.position} generado."
            )
        )

    except Scene.DoesNotExist:

        messages.error(
            request,
            "La escena solicitada no existe."
        )

    except Exception as exc:

        messages.error(
            request,
            f"Error generando video: {exc}"
        )

    return redirect(
        "videos_workspace",
        project.id
    )


@login_required
def generate_all_videos_view(
    request,
    project_id,
):
    if request.method != "POST":

        return redirect(
            "videos_workspace",
            project_id
        )

    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    from generations.video_services import (
        generate_all_scene_videos,
    )

    provider_code = os.environ.get(
        "GINGAO_VIDEO_PROVIDER",
        "mock"
    ).lower()

    if (
        provider_code != "mock"
        and os.environ.get(
            "GINGAO_ALLOW_REAL_VIDEO_BULK",
            "0"
        ) != "1"
    ):
        messages.warning(
            request,
            "Generacion masiva de video real "
            "bloqueada por seguridad."
        )

        return redirect(
            "videos_workspace",
            project.id
        )

    try:

        results = (
            generate_all_scene_videos(
                project=project,
                user=request.user,
                provider_code=provider_code,
            )
        )

        messages.success(
            request,
            f"{len(results)} videos generados."
        )

    except Exception as exc:

        messages.error(
            request,
            f"Error generando videos: {exc}"
        )

    return redirect(
        "videos_workspace",
        project.id
    )



@login_required
def upload_scene_image_view(
    request,
    project_id,
    scene_id,
):
    if request.method != "POST":

        return redirect(
            "images_workspace",
            project_id
        )

    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    scene = get_object_or_404(
        project.scenes,
        id=scene_id,
    )

    uploaded_file = (
        request.FILES.get(
            "scene_image"
        )
    )

    from projects.upload_services import (
        save_scene_upload,
    )

    try:

        result = save_scene_upload(
            uploaded_file=uploaded_file,
            project=project,
            scene=scene,
            user=request.user,
        )

        if result["asset"] is None:

            messages.warning(
                request,
                "Imagen subida correctamente, "
                "pero el Asset no pudo "
                "registrarse automaticamente."
            )

        else:

            messages.success(
                request,
                f"Imagen real asignada "
                f"a la escena "
                f"{scene.position}."
            )

    except Exception as exc:

        messages.error(
            request,
            f"Error subiendo imagen: {exc}"
        )

    return redirect(
        "images_workspace",
        project.id
    )





# ============================================================================
# GINGAO_SMART_MULTI_IMAGE_UPLOAD_V35
# ============================================================================

@login_required
def upload_all_scene_images_view(
    request,
    project_id,
):
    """
    Smart multi-image upload.

    Rules:
    - if user uploads exactly one image per project scene,
      replace all scenes in order;
    - otherwise assign selected files only to scenes that
      do not yet have a real raster image;
    - existing real images are preserved by default.
    """

    if request.method != "POST":

        return redirect(
            "images_workspace",
            project_id
        )

    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    uploaded_files = list(
        request.FILES.getlist(
            "scene_images"
        )
    )

    if not uploaded_files:

        messages.warning(
            request,
            "Selecciona al menos una imagen."
        )

        return redirect(
            "images_workspace",
            project.id
        )

    scenes = list(
        project.scenes
        .select_related(
            "storyboard_image"
        )
        .order_by(
            "position"
        )
    )

    if not scenes:

        messages.error(
            request,
            "El proyecto no tiene escenas."
        )

        return redirect(
            "images_workspace",
            project.id
        )

    if len(uploaded_files) > len(scenes):

        messages.error(
            request,
            "Has seleccionado mas imagenes "
            "que escenas tiene el proyecto."
        )

        return redirect(
            "images_workspace",
            project.id
        )

    real_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
    }

    pending_scenes = []

    for scene in scenes:

        try:

            image_url = (
                scene.storyboard_image.image_url
                or ""
            )

        except Exception:

            image_url = ""

        suffix = Path(
            str(image_url).split("?")[0]
        ).suffix.lower()

        is_real = (
            bool(image_url)
            and suffix
            in real_extensions
        )

        if not is_real:

            pending_scenes.append(
                scene
            )

    # Exact project scene count means explicit full replacement.
    if len(uploaded_files) == len(scenes):

        target_scenes = scenes
        assignment_mode = "all"

    else:

        if not pending_scenes:

            messages.info(
                request,
                "Todas las escenas ya tienen "
                "una imagen real."
            )

            return redirect(
                "images_workspace",
                project.id
            )

        if (
            len(uploaded_files)
            > len(pending_scenes)
        ):

            messages.error(
                request,
                f"Hay {len(pending_scenes)} "
                "escenas pendientes, pero has "
                f"seleccionado "
                f"{len(uploaded_files)} imagenes. "
                "Selecciona solo las pendientes "
                "o una imagen por cada escena "
                "para reemplazarlas todas."
            )

            return redirect(
                "images_workspace",
                project.id
            )

        target_scenes = (
            pending_scenes[
                :len(uploaded_files)
            ]
        )

        assignment_mode = "pending"

    from projects.upload_services import (
        save_scene_upload,
    )

    successful = []
    asset_warnings = []
    failures = []

    for uploaded_file, scene in zip(
        uploaded_files,
        target_scenes,
    ):

        try:

            result = save_scene_upload(
                uploaded_file=uploaded_file,
                project=project,
                scene=scene,
                user=request.user,
            )

            successful.append(
                scene.position
            )

            if result.get("asset") is None:

                asset_warnings.append(
                    scene.position
                )

        except Exception as exc:

            failures.append(
                (
                    scene.position,
                    str(exc),
                )
            )

    if successful:

        scene_text = ", ".join(
            str(position)
            for position in successful
        )

        if assignment_mode == "all":

            message = (
                f"{len(successful)} imagenes "
                "asignadas. Se reemplazo el "
                "storyboard visual por orden "
                f"en las escenas: {scene_text}."
            )

        else:

            message = (
                f"{len(successful)} imagenes "
                "reales asignadas por orden "
                "a las escenas pendientes: "
                f"{scene_text}."
            )

        messages.success(
            request,
            message
        )

    if asset_warnings:

        messages.warning(
            request,
            "Las imagenes fueron asignadas, "
            "pero algunas no pudieron "
            "registrarse en Mis activos: "
            + ", ".join(
                str(position)
                for position
                in asset_warnings
            )
            + "."
        )

    if failures:

        failure_text = "; ".join(
            (
                f"escena {position}: "
                f"{error}"
            )
            for position, error
            in failures
        )

        messages.error(
            request,
            "No se pudieron subir algunas "
            "imagenes: "
            + failure_text
        )

    return redirect(
        "images_workspace",
        project.id
    )


@login_required
def final_cut_view(
    request,
    project_id,
):
    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    wallet = _wallet_for(
        request.user
    )

    from generations.final_services import (
        get_project_video_timeline,
        get_project_visual_coverage,
    )

    timeline, total_duration = (
        get_project_video_timeline(
            project
        )
    )

    from generations.audio_services import (
        get_project_audio_info,
    )

    audio_info = get_project_audio_info(
        project=project,
        user=request.user,
    )


    visual_coverage = (
        get_project_visual_coverage(
            project
        )
    )


    stored_final_url = request.session.get(
        f"gingao_final_{project.id}",
        "",
    )

    final_export_url = (
        stored_final_url
        if str(
            stored_final_url
            or ""
        ).lower().endswith(".mp4")
        else ""
    )

    ready_count = sum(
        1
        for item in timeline
        if item["ready"]
    )

    all_ready = (
        bool(timeline)
        and ready_count
        == len(timeline)
    )

    return render(
        request,
        "dashboard/final_cut.html",
        {
            "project": project,
            "wallet": wallet,
            "timeline": timeline,
            "total_duration":
                total_duration,
            "ready_count":
                ready_count,
            "scene_count":
                len(timeline),
            "all_ready":
                all_ready,
            "audio_info":
                audio_info,
            "visual_coverage":
                visual_coverage,
            "final_export_url":
                final_export_url,
            "audio_provider_code":
                os.environ.get(
                    "GINGAO_AUDIO_PROVIDER",
                    "mock"
                ).lower(),
        }
    )


@login_required
def export_final_cut_view(
    request,
    project_id,
):
    if request.method != "POST":

        return redirect(
            "final_cut",
            project_id
        )

    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    from generations.final_services import (
        create_local_final_mp4,
    )

    export_quality = str(
        request.POST.get(
            "export_quality",
            project.quality_tier,
        )
        or project.quality_tier
        or "standard"
    ).strip().lower()

    valid_export_qualities = {
        "fast",
        "standard",
        "premium",
    }

    if export_quality not in valid_export_qualities:
        export_quality = "standard"

    try:

        result = create_local_final_mp4(
            project=project,
            user=request.user,
            quality_tier=export_quality,
        )

        request.session[
            f"gingao_final_{project.id}"
        ] = result["url"]

        audio_state = (
            " con audio sincronizado"
            if result.get("has_audio")
            else " sin audio"
        )

        message = (
            "MP4 final generado "
            f"({result['duration']} s)"
            f"{audio_state}. "
            f"Formato {project.aspect_ratio}. "
            f"Calidad {result['quality_tier']}."
        )

        if result["asset"] is None:

            message += (
                " El manifiesto fue creado, "
                "pero el Asset final no pudo "
                "registrarse porque falta "
                f"'{result['asset_missing_field']}'."
            )

        messages.success(
            request,
            message
        )

    except Exception as exc:

        messages.error(
            request,
            f"Error preparando corte final: {exc}"
        )

    return redirect(
        "final_cut",
        project.id
    )



@login_required
def generate_project_audio_view(
    request,
    project_id,
):
    # GINGAO_AUDIO_GENERATION_GUARD_V49C

    if request.method != "POST":

        return redirect(
            "final_cut",
            project_id
        )

    from django.db import transaction

    from credits.services import (
        InsufficientCredits,
        reserve_credits,
        refund_credits,
    )

    from generations.audio_services import (
        generate_project_audio,
        project_duration,
    )

    from generations.job_services import (
        create_job,
        mark_processing,
        mark_completed,
        mark_failed,
    )

    from generations.models import (
        GenerationJob,
    )

    from generations.pricing import (
        estimate_audio_cost,
    )

    project = get_object_or_404(
        Project,
        id=project_id,
        owner=request.user,
    )

    if not bool(
        getattr(
            project,
            "voice_enabled",
            True,
        )
    ):

        messages.warning(
            request,
            "Este proyecto tiene la narracion "
            "desactivada."
        )

        return redirect(
            "final_cut",
            project.id
        )

    provider_code = (
        os.environ.get(
            "GINGAO_AUDIO_PROVIDER",
            "mock"
        )
        .strip()
        .lower()
    )

    job = None
    reserved_credits = 0

    try:

        with transaction.atomic():

            project = (
                Project.objects
                .select_for_update()
                .get(
                    id=project.id,
                    owner=request.user,
                )
            )

            job, created = create_job(
                user=request.user,
                project=project,
                job_type=(
                    GenerationJob.TYPE_AUDIO
                ),
                scene=None,
                provider=provider_code,
                payload={
                    "project_id":
                        project.id,

                    "voice_preset":
                        getattr(
                            project,
                            "voice_preset",
                            "",
                        ),
                },
            )

            if not created:

                messages.warning(
                    request,
                    "La narracion ya se esta "
                    "generando. No se ha iniciado "
                    "una segunda solicitud."
                )

                return redirect(
                    "final_cut",
                    project.id
                )

            duration = project_duration(
                project
            )

            estimate = estimate_audio_cost(
                duration
            )

            reserved_credits = int(
                estimate.internal_credits
                or 0
            )

            if reserved_credits > 0:

                reserve_credits(
                    request.user,
                    reserved_credits,
                    reference=(
                        f"audio-generation:{job.id}"
                    ),
                )

            mark_processing(
                job.id
            )

        try:

            result = generate_project_audio(
                project=project,
                user=request.user,
                provider_code=provider_code,
            )

            result_url = (
                result.get("url")
                or ""
            )

            if not result_url:

                raise RuntimeError(
                    "El proveedor no devolvio "
                    "una URL de audio."
                )

            mark_completed(
                job_id=job.id,
                result_url=result_url,
            )

        except Exception as exc:

            mark_failed(
                job_id=job.id,
                error_message=str(exc),
            )

            if reserved_credits > 0:

                refund_credits(
                    request.user,
                    reserved_credits,
                    reference=(
                        f"audio-refund:{job.id}"
                    ),
                )

            raise

        if provider_code == "elevenlabs":

            message = (
                "Narracion IA preparada "
                f"({result['duration']} s)."
            )

        else:

            message = (
                "Narracion Mock preparada "
                f"({result['duration']} s)."
            )

        if result["asset"] is None:

            message += (
                " El archivo fue creado, "
                "pero no pudo registrarse "
                "como Asset porque falta "
                f"'{result['asset_missing_field']}'."
            )

        messages.success(
            request,
            message
        )

    except InsufficientCredits:

        if job is not None:

            mark_failed(
                job_id=job.id,
                error_message=(
                    "Creditos insuficientes."
                ),
            )

        messages.error(
            request,
            "No tienes creditos suficientes "
            "para generar esta narracion."
        )

    except Exception as exc:

        messages.error(
            request,
            f"Error generando audio: {exc}"
        )

    return redirect(
        "final_cut",
        project.id
    )



@login_required
def system_status_view(
    request,
):

    from config.runtime import (
        get_runtime_config,
        production_ready,
        production_warnings,
    )

    from generations.pricing import (
        estimate_project_cost,
    )

    cfg = get_runtime_config()

    from credits.nowpayments import (
        get_live_readiness,
        check_nowpayments_connectivity,
    )

    nowpayments_readiness = (
        get_live_readiness()
    )

    nowpayments_connectivity = {
        "api_status": False,
        "api_key": False,
        "ready": False,
        "error": "",
    }

    if nowpayments_readiness["ready"]:
        nowpayments_connectivity = (
            check_nowpayments_connectivity()
        )

    from config.security import (
        security_ready,
        security_snapshot,
        security_warnings,
    )

    security_info = (
        security_snapshot()
    )

    projects = (
        Project.objects
        .filter(
            owner=request.user
        )
        .order_by(
            "-updated_at"
        )
    )

    selected_project = (
        projects.first()
    )

    cost = None

    if selected_project is not None:

        cost = estimate_project_cost(
            selected_project
        )

    return render(
        request,
        "dashboard/system_status.html",
        {
            "wallet":
                _wallet_for(
                    request.user
                ),

            "runtime":
                cfg,

            "production_ready":
                production_ready(),

            "production_warnings":
                production_warnings(),

            "security_ready":
                security_ready(),

            "security_warnings":
                security_warnings(),

            "security_info":
                security_info,

            "nowpayments_readiness":
                nowpayments_readiness,

            "nowpayments_connectivity":
                nowpayments_connectivity,

            "selected_project":
                selected_project,

            "cost":
                cost,
        }
    )



@login_required
def billing_page(
    request,
):
    from credits.plans import (
        all_plans,
    )

    from credits.commerce import (
        transaction_display,
        transaction_history,
    )

    wallet = _wallet_for(
        request.user
    )

    raw_history = (
        transaction_history(
            request.user,
            limit=30,
        )
    )

    history = [
        transaction_display(tx)
        for tx in raw_history
    ]

    return render(
        request,
        "dashboard/billing.html",
        {
            "wallet": wallet,
            "plans": all_plans(),
            "history": history,
            "payments_live": getattr(
                __import__(
                    "django.conf",
                    fromlist=["settings"],
                ).settings,
                "GINGAO_PAYMENTS_LIVE",
                False,
            ),
        }
    )


@login_required
def simulate_purchase_view(
    request,
    plan_code,
):
    from django.conf import settings

    if not getattr(
        settings,
        "GINGAO_MOCK_PAYMENTS_ENABLED",
        False,
    ):
        messages.error(
            request,
            "La compra simulada no esta disponible."
        )
        return redirect("billing")

    if request.method != "POST":
        return redirect("billing")

    from credits.commerce import (
        simulate_plan_purchase,
    )

    try:
        plan, result = simulate_plan_purchase(
            user=request.user,
            plan_code=plan_code,
        )

        messages.success(
            request,
            (
                f"Compra simulada: "
                f"{plan.name}. "
                f"+{result.amount} creditos."
            ),
        )

    except Exception as exc:
        messages.error(
            request,
            f"No se pudo completar: {exc}",
        )

    return redirect("billing")


@login_required
def payment_checkout_view(
    request,
    plan_code,
    payment_method,
):
    if request.method != "POST":

        return redirect(
            "billing"
        )

    from credits.payment_services import (
        create_payment,
    )

    from credits.nowpayments import (
        is_trusted_nowpayments_checkout_url,
    )

    try:

        payment = create_payment(
            user=request.user,
            plan_code=plan_code,
            payment_method=payment_method,
            request=request,
        )

        if (
            payment.payment_method == "card"
            and payment.provider == "nowpayments"
            and payment.checkout_url
            and is_trusted_nowpayments_checkout_url(
                payment.checkout_url
            )
        ):
            return redirect(
                payment.checkout_url
            )

        return redirect(
            "payment_detail",
            payment.id
        )

    except Exception as exc:

        messages.error(
            request,
            f"Error creando pago: {exc}"
        )

        return redirect(
            "billing"
        )


@login_required
def payment_detail_view(
    request,
    payment_id,
):
    from credits.models import Payment

    from credits.nowpayments import (
        is_trusted_nowpayments_checkout_url,
    )

    payment = get_object_or_404(
        Payment,
        id=payment_id,
        user=request.user,
    )

    safe_checkout_url = ""

    if (
        payment.provider == "nowpayments"
        and payment.checkout_url
        and is_trusted_nowpayments_checkout_url(
            payment.checkout_url
        )
    ):
        safe_checkout_url = payment.checkout_url

    return render(
        request,
        "dashboard/payment_detail.html",
        {
            "payment": payment,
            "safe_checkout_url":
                safe_checkout_url,
            "wallet": _wallet_for(
                request.user
            ),
            "payments_live": getattr(
                __import__(
                    "django.conf",
                    fromlist=["settings"],
                ).settings,
                "GINGAO_PAYMENTS_LIVE",
                False,
            ),
        }
    )


@login_required
def payment_mock_success_view(
    request,
    payment_id,
):
    from django.conf import settings
    from credits.models import Payment

    if not getattr(
        settings,
        "GINGAO_MOCK_PAYMENTS_ENABLED",
        False,
    ):
        messages.error(
            request,
            "La confirmacion Mock no esta disponible."
        )
        return redirect("billing")

    if request.method != "POST":
        return redirect(
            "payment_detail",
            payment_id,
        )

    # SECURITY:
    # ownership is checked BEFORE confirm_payment().
    payment = get_object_or_404(
        Payment,
        id=payment_id,
        user=request.user,
    )

    from credits.payment_services import (
        confirm_payment,
    )

    try:
        payment, credited = confirm_payment(
            payment_id=payment.id,
        )

        if credited:
            messages.success(
                request,
                (
                    f"Pago confirmado. "
                    f"+{payment.credits} creditos."
                ),
            )
        else:
            messages.info(
                request,
                "El pago ya habia sido acreditado.",
            )

    except Exception as exc:
        messages.error(
            request,
            f"No se pudo confirmar el pago: {exc}",
        )

    return redirect(
        "payment_detail",
        payment.id,
    )


@login_required
def payment_mock_fail_view(
    request,
    payment_id,
):
    from django.conf import settings
    from credits.models import Payment

    if not getattr(
        settings,
        "GINGAO_MOCK_PAYMENTS_ENABLED",
        False,
    ):
        messages.error(
            request,
            "El fallo Mock no esta disponible."
        )
        return redirect("billing")

    if request.method != "POST":
        return redirect(
            "payment_detail",
            payment_id,
        )

    # Ownership must be checked before mutating payment state.
    payment = get_object_or_404(
        Payment,
        id=payment_id,
        user=request.user,
    )

    from credits.payment_services import (
        fail_payment,
    )

    try:
        payment = fail_payment(
            payment_id=payment.id,
        )

        messages.error(
            request,
            "Pago marcado como fallido.",
        )

    except Exception as exc:
        messages.error(
            request,
            f"No se pudo marcar el pago: {exc}",
        )

    return redirect(
        "payment_detail",
        payment.id,
    )


@login_required
def jobs_page(
    request,
):
    from generations.models import (
        GenerationJob,
    )

    jobs = (
        GenerationJob.objects
        .filter(
            user=request.user
        )
        .select_related(
            "project",
            "scene",
        )
        .order_by(
            "-created_at"
        )[:50]
    )

    stats = {
        "queued":
            GenerationJob.objects.filter(
                user=request.user,
                status=(
                    GenerationJob.STATUS_QUEUED
                ),
            ).count(),

        "processing":
            GenerationJob.objects.filter(
                user=request.user,
                status=(
                    GenerationJob.STATUS_PROCESSING
                ),
            ).count(),

        "completed":
            GenerationJob.objects.filter(
                user=request.user,
                status=(
                    GenerationJob.STATUS_COMPLETED
                ),
            ).count(),

        "failed":
            GenerationJob.objects.filter(
                user=request.user,
                status=(
                    GenerationJob.STATUS_FAILED
                ),
            ).count(),
    }

    return render(
        request,
        "dashboard/jobs.html",
        {
            "jobs": jobs,
            "stats": stats,
            "wallet": _wallet_for(
                request.user
            ),
        }
    )


@login_required
def retry_job_view(
    request,
    job_id,
):
    if request.method != "POST":
        return redirect(
            "jobs"
        )

    from generations.models import (
        GenerationJob,
    )

    from generations.job_services import (
        can_retry,
        create_job,
    )

    from generations.tasks import (
        execute_generation_job_task,
    )

    job = get_object_or_404(
        GenerationJob,
        id=job_id,
        user=request.user,
    )

    if not can_retry(job):

        messages.warning(
            request,
            "Este trabajo no puede reintentarse."
        )

        return redirect(
            "jobs"
        )

    new_job, created = create_job(
        user=request.user,
        project=job.project,
        scene=job.scene,
        job_type=job.job_type,
        provider=job.provider,
        payload=job.payload,
    )

    if created:

        try:
            execute_generation_job_task.delay(
                new_job.id
            )

            messages.success(
                request,
                "Trabajo reintentado correctamente."
            )

        except Exception as exc:

            messages.error(
                request,
                f"El reintento fallo: {exc}"
            )

    return redirect(
        "jobs"
    )



def health_check_view(
    request,
):
    from django.http import JsonResponse

    from config.health import (
        get_health_snapshot,
    )

    snapshot = (
        get_health_snapshot()
    )

    status_code = (
        200
        if snapshot["database"]
        == "ok"
        else 503
    )

    return JsonResponse(
        snapshot,
        status=status_code,
    )


# =============================================================================
# GINGAO_JOB_STATUS_API_V46D
# =============================================================================

@login_required
def job_status_view(
    request,
    job_id,
):

    from generations.models import (
        GenerationJob,
    )

    job = get_object_or_404(
        GenerationJob,
        id=job_id,
        user=request.user,
    )

    terminal = job.status in {
        GenerationJob.STATUS_COMPLETED,
        GenerationJob.STATUS_FAILED,
    }

    return JsonResponse({
        "id":
            job.id,

        "job_type":
            job.job_type,

        "status":
            job.status,

        "provider":
            job.provider,

        "attempts":
            job.attempts,

        "max_attempts":
            job.max_attempts,

        "result_url":
            job.result_url or "",

        "error_message":
            job.error_message or "",

        "terminal":
            terminal,

        "updated_at":
            (
                job.updated_at.isoformat()
                if job.updated_at
                else ""
            ),
    })

