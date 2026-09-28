from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from credits.qr_views import payment_qr_view

from credits.webhook_views import nowpayments_webhook_view

from projects.views import (
    assets_page,
    billing_page,
    payment_mock_fail_view,
    payment_mock_success_view,
    payment_detail_view,
    payment_checkout_view,
    create_video,
    export_final_cut_view,
    final_cut_view,
    generate_all_images_view,
    generate_all_videos_view,
    generate_project_audio_view,
    generate_scene_image_view,
    generate_scene_video_view,
    generate_script_view,
    home,
    health_check_view,
    jobs_page,
    job_status_view,
    retry_job_view,
    images_workspace,
    login_view,
    logout_view,
    prepare_images_view,
    profile_page,
    project_workspace,
    projects_page,
    register_view,
    system_status_view,
    simulate_purchase_view,
    upload_scene_image_view,
    upload_all_scene_images_view,
    videos_workspace,
)


urlpatterns = [
    path(
        "health/",
        health_check_view,
        name="health_check"
    ),

    path(
        "admin/",
        admin.site.urls
    ),

    path(
        "login/",
        login_view,
        name="login"
    ),

    path(
        "register/",
        register_view,
        name="register"
    ),

    path(
        "logout/",
        logout_view,
        name="logout"
    ),

    path(
        "",
        home,
        name="home"
    ),

    path(
        "projects/",
        projects_page,
        name="projects"
    ),

    path(
        "assets/",
        assets_page,
        name="assets"
    ),

    path(
        "profile/",
        profile_page,
        name="profile"
    ),

    path(
        "system/status/",
        system_status_view,
        name="system_status"
    ),

    path(
        "jobs/",
        jobs_page,
        name="jobs"
    ),

    path(
        "jobs/<int:job_id>/status/",
        job_status_view,
        name="job_status"
    ),

    path(
        "jobs/<int:job_id>/retry/",
        retry_job_view,
        name="retry_job"
    ),

    path(
        "billing/",
        billing_page,
        name="billing"
    ),

    path(
        "billing/webhook/nowpayments/",
        nowpayments_webhook_view,
        name="nowpayments_webhook"
    ),

    path(
        "billing/checkout/<str:plan_code>/<str:payment_method>/",
        payment_checkout_view,
        name="payment_checkout"
    ),

    path(
        "billing/payment/<int:payment_id>/",
        payment_detail_view,
        name="payment_detail"
    ),

    path(
        "billing/payment/<int:payment_id>/qr/",
        payment_qr_view,
        name="payment_qr"
    ),

    path(
        "billing/payment/<int:payment_id>/mock-success/",
        payment_mock_success_view,
        name="payment_mock_success"
    ),

    path(
        "billing/payment/<int:payment_id>/mock-fail/",
        payment_mock_fail_view,
        name="payment_mock_fail"
    ),

    path(
        "billing/buy/<str:plan_code>/",
        simulate_purchase_view,
        name="simulate_purchase"
    ),

    path(
        "create/",
        create_video,
        name="create_video"
    ),

    path(
        "projects/<int:project_id>/generate-script/",
        generate_script_view,
        name="generate_script"
    ),

    path(
        "projects/<int:project_id>/images/",
        images_workspace,
        name="images_workspace"
    ),

    path(
        "projects/<int:project_id>/prepare-images/",
        prepare_images_view,
        name="prepare_images"
    ),

    path(
        "projects/<int:project_id>/images/"
        "<int:scene_id>/generate/",
        generate_scene_image_view,
        name="generate_scene_image"
    ),

    path(
        "projects/<int:project_id>/images/"
        "<int:scene_id>/upload/",
        upload_scene_image_view,
        name="upload_scene_image"
    ),

    path(
        "projects/<int:project_id>/images/"
        "upload-all/",
        upload_all_scene_images_view,
        name="upload_all_scene_images"
    ),


    path(
        "projects/<int:project_id>/images/generate-all/",
        generate_all_images_view,
        name="generate_all_images"
    ),

    path(
        "projects/<int:project_id>/videos/",
        videos_workspace,
        name="videos_workspace"
    ),

    path(
        "projects/<int:project_id>/videos/"
        "<int:scene_id>/generate/",
        generate_scene_video_view,
        name="generate_scene_video"
    ),

    path(
        "projects/<int:project_id>/videos/generate-all/",
        generate_all_videos_view,
        name="generate_all_videos"
    ),

    path(
        "projects/<int:project_id>/final/",
        final_cut_view,
        name="final_cut"
    ),

    path(
        "projects/<int:project_id>/final/export/",
        export_final_cut_view,
        name="export_final_cut"
    ),

    path(
        "projects/<int:project_id>/final/audio/",
        generate_project_audio_view,
        name="generate_project_audio"
    ),

    path(
        "projects/<int:project_id>/",
        project_workspace,
        name="project_workspace"
    ),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
