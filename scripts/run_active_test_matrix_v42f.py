from pathlib import Path
import subprocess
import time
import hashlib
import shutil
import json
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

DB = ROOT / "db.sqlite3"
DB_BACKUP = ROOT / ".v42f_db_backup.sqlite3"

OUT_TXT = ROOT / "v42f_test_matrix.txt"
OUT_JSON = ROOT / "v42f_test_matrix.json"

TIMEOUT_SECONDS = 120


def sha256(path):

    if not path.exists():
        return None

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def generated_snapshot():

    roots = [
        ROOT / "static" / "generated" / "mock",
        ROOT / "static" / "generated" / "video_mock",
        ROOT / "static" / "generated" / "audio_mock",
    ]

    result = {}

    for folder in roots:

        if not folder.exists():
            continue

        for path in folder.rglob("*"):

            if path.is_file():

                result[
                    str(
                        path.relative_to(ROOT)
                    ).replace("\\", "/")
                ] = path.stat().st_size

    return result


def restore_db():

    if (
        DB_BACKUP.exists()
        and DB.exists()
    ):
        shutil.copy2(
            DB_BACKUP,
            DB,
        )


tests = sorted(
    [
        p
        for p in SCRIPTS.glob("*.py")
        if (
            p.name.startswith("audit_")
            or p.name.startswith("validate_")
            or p.name.startswith("inspect_")
        )
        and p.name != Path(__file__).name
    ]
)


print()
print("=" * 110)
print("GINGAO V42F - ACTIVE TEST EXECUTION MATRIX")
print("=" * 110)

print(
    "Active tests:",
    len(tests)
)


if DB.exists():

    shutil.copy2(
        DB,
        DB_BACKUP,
    )

    original_db_hash = sha256(
        DB
    )

else:

    original_db_hash = None


results = []


try:

    for index, script in enumerate(
        tests,
        start=1,
    ):

        print()
        print(
            f"[{index}/{len(tests)}] "
            f"{script.name}"
        )

        # Always restore pristine DB before test.
        if DB_BACKUP.exists():
            restore_db()

        db_before = sha256(
            DB
        )

        generated_before = (
            generated_snapshot()
        )

        start = time.perf_counter()

        timed_out = False
        return_code = None
        stdout = ""
        stderr = ""


        try:

            proc = subprocess.run(
                [
                    sys.executable,
                    str(script),
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                env=os.environ.copy(),
            )

            return_code = (
                proc.returncode
            )

            stdout = (
                proc.stdout or ""
            )

            stderr = (
                proc.stderr or ""
            )


        except subprocess.TimeoutExpired as exc:

            timed_out = True

            stdout = (
                exc.stdout
                if isinstance(
                    exc.stdout,
                    str,
                )
                else ""
            )

            stderr = (
                exc.stderr
                if isinstance(
                    exc.stderr,
                    str,
                )
                else ""
            )


        duration = (
            time.perf_counter()
            - start
        )


        db_after = sha256(
            DB
        )

        db_changed = (
            db_before != db_after
        )


        generated_after = (
            generated_snapshot()
        )


        created_files = sorted(
            set(generated_after)
            - set(generated_before)
        )


        removed_files = sorted(
            set(generated_before)
            - set(generated_after)
        )


        changed_files = sorted(
            key
            for key in (
                set(generated_before)
                & set(generated_after)
            )
            if (
                generated_before[key]
                != generated_after[key]
            )
        )


        if timed_out:
            status = "TIMEOUT"

        elif return_code == 0:
            status = "PASS"

        else:
            status = "FAIL"


        # Restore DB immediately if touched.
        if (
            db_changed
            and DB_BACKUP.exists()
        ):

            restore_db()


        # Keep output compact.
        stdout_tail = "\n".join(
            stdout.splitlines()[-12:]
        )

        stderr_tail = "\n".join(
            stderr.splitlines()[-12:]
        )


        item = {
            "script":
                script.name,

            "status":
                status,

            "return_code":
                return_code,

            "duration_seconds":
                round(
                    duration,
                    3,
                ),

            "db_changed":
                db_changed,

            "generated_created":
                created_files,

            "generated_removed":
                removed_files,

            "generated_changed":
                changed_files,

            "stdout_tail":
                stdout_tail,

            "stderr_tail":
                stderr_tail,
        }

        results.append(
            item
        )


        print(
            "  status:",
            status
        )

        print(
            "  duration:",
            f"{duration:.2f}s"
        )

        print(
            "  db changed:",
            db_changed
        )

        print(
            "  generated created:",
            len(created_files)
        )

        print(
            "  generated removed:",
            len(removed_files)
        )

        print(
            "  generated changed:",
            len(changed_files)
        )


finally:

    if DB_BACKUP.exists():

        restore_db()

        DB_BACKUP.unlink()


# ============================================================================
# FINAL DB SAFETY
# ============================================================================

final_db_hash = sha256(
    DB
)

db_restored = (
    original_db_hash
    == final_db_hash
)


# ============================================================================
# SUMMARY
# ============================================================================

summary = {
    "PASS": 0,
    "FAIL": 0,
    "TIMEOUT": 0,
}

for item in results:

    summary[
        item["status"]
    ] += 1


print()
print("=" * 110)
print("V42F SUMMARY")
print("=" * 110)

print(
    "PASS:",
    summary["PASS"]
)

print(
    "FAIL:",
    summary["FAIL"]
)

print(
    "TIMEOUT:",
    summary["TIMEOUT"]
)

print(
    "DATABASE RESTORED:",
    db_restored
)


# ============================================================================
# TXT REPORT
# ============================================================================

lines = []

lines.append(
    "GINGAO V42F ACTIVE TEST MATRIX"
)

lines.append("")

lines.append(
    f"PASS: {summary['PASS']}"
)

lines.append(
    f"FAIL: {summary['FAIL']}"
)

lines.append(
    f"TIMEOUT: {summary['TIMEOUT']}"
)

lines.append(
    f"DATABASE_RESTORED: {db_restored}"
)


for item in results:

    lines.append("")
    lines.append(
        "=" * 100
    )

    lines.append(
        item["script"]
    )

    lines.append(
        "=" * 100
    )

    lines.append(
        f"status={item['status']}"
    )

    lines.append(
        f"duration={item['duration_seconds']}"
    )

    lines.append(
        f"db_changed={item['db_changed']}"
    )

    lines.append(
        "generated_created="
        + ",".join(
            item[
                "generated_created"
            ]
        )
    )

    lines.append(
        "generated_removed="
        + ",".join(
            item[
                "generated_removed"
            ]
        )
    )

    lines.append(
        "generated_changed="
        + ",".join(
            item[
                "generated_changed"
            ]
        )
    )

    if (
        item["status"]
        != "PASS"
    ):

        lines.append(
            "STDOUT_TAIL:"
        )

        lines.append(
            item[
                "stdout_tail"
            ]
        )

        lines.append(
            "STDERR_TAIL:"
        )

        lines.append(
            item[
                "stderr_tail"
            ]
        )


OUT_TXT.write_text(
    "\n".join(lines),
    encoding="utf-8",
)


OUT_JSON.write_text(
    json.dumps(
        {
            "summary":
                summary,

            "database_restored":
                db_restored,

            "results":
                results,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


print()
print(
    "TEXT REPORT:",
    OUT_TXT
)

print(
    "JSON REPORT:",
    OUT_JSON
)

print()
print("=" * 110)
print("GINGAO V42F MATRIX COMPLETE")
print("=" * 110)


if not db_restored:

    raise RuntimeError(
        "Database hash differs after V42F."
    )
