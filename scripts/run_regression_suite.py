from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

TESTS = [
    "audit_cleanup_v41b.py",
    "audit_final_dynamic_timing_v7.py",
    "audit_final_export_v31.py",
    "audit_generation_profiles_v40a.py",
    "audit_master_audio_sync_v30.py",
    "audit_production_options_v37.py",
    "audit_quality_pipeline_v39c.py",
    "audit_real_storyboard_v3.py",
    "audit_smart_multi_image_upload_v35.py",
    "audit_visual_coverage_v34.py",
    "validate_costs.py",
    "validate_create_flow_v38.py",
    "validate_credit_flow.py",
    "validate_internal_pipeline_v40c.py",
    "validate_mock_generation_v40b.py",
    "validate_models.py",
    "validate_real_render_v39b.py",
    "validate_video_asset_flow_v40d1.py",
]


print()
print("=" * 100)
print("GINGAO PERMANENT REGRESSION SUITE")
print("=" * 100)

passed = 0
failed = []

suite_start = time.perf_counter()


for index, name in enumerate(
    TESTS,
    start=1,
):

    path = (
        SCRIPTS
        / name
    )

    if not path.exists():

        print(
            f"[{index}/{len(TESTS)}] "
            f"{name}: MISSING"
        )

        failed.append(
            (
                name,
                "MISSING",
            )
        )

        continue


    start = time.perf_counter()

    result = subprocess.run(
        [
            sys.executable,
            str(path),
        ],
        cwd=str(ROOT),
    )

    duration = (
        time.perf_counter()
        - start
    )


    if result.returncode == 0:

        status = "PASS"
        passed += 1

    else:

        status = "FAIL"

        failed.append(
            (
                name,
                result.returncode,
            )
        )


    print(
        f"[{index}/{len(TESTS)}] "
        f"{name}: {status} "
        f"({duration:.2f}s)"
    )


total_duration = (
    time.perf_counter()
    - suite_start
)


print()
print("=" * 100)
print("REGRESSION SUMMARY")
print("=" * 100)

print(
    "PASS:",
    passed
)

print(
    "FAIL:",
    len(failed)
)

print(
    "TOTAL:",
    len(TESTS)
)

print(
    "DURATION:",
    f"{total_duration:.2f}s"
)


if failed:

    print()
    print("FAILED TESTS:")

    for name, result in failed:

        print(
            "-",
            name,
            result,
        )

    raise SystemExit(1)


print()
print(
    "GINGAO REGRESSION SUITE: OK"
)
