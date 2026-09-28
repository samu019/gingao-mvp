from datetime import timedelta

from django.core.files.storage import default_storage
from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.utils import timezone


DEFAULT_PREFIX = "generated"


def _normalize_prefix(
    value,
):
    value = str(
        value
        or DEFAULT_PREFIX
    ).replace(
        "\\",
        "/",
    ).strip()

    value = value.strip("/")

    if not value:
        return DEFAULT_PREFIX

    if (
        value == ".."
        or value.startswith("../")
        or "/../" in value
    ):
        raise CommandError(
            "Invalid storage prefix."
        )

    return value


def _iter_storage_files(
    prefix,
):
    """
    Recursively enumerate files through Django storage.

    Compatible with filesystem and object-storage backends
    that implement the standard Storage.listdir() contract.
    """

    directories, files = (
        default_storage.listdir(
            prefix
        )
    )

    for filename in files:

        yield (
            prefix.rstrip("/")
            + "/"
            + filename
        )

    for directory in directories:

        child = (
            prefix.rstrip("/")
            + "/"
            + directory
        )

        yield from _iter_storage_files(
            child
        )


def _modified_time(
    storage_name,
):
    modified = (
        default_storage.get_modified_time(
            storage_name
        )
    )

    if timezone.is_naive(
        modified
    ):
        modified = timezone.make_aware(
            modified,
            timezone.get_current_timezone(),
        )

    return modified


class Command(BaseCommand):

    help = (
        "Delete old generated files "
        "through Django default_storage."
    )

    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "--days",
            type=int,
            default=30,
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
        )

        parser.add_argument(
            "--prefix",
            default=DEFAULT_PREFIX,
            help=(
                "Storage prefix to inspect. "
                "Default: generated"
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):

        days = max(
            int(
                options["days"]
            ),
            1,
        )

        dry_run = bool(
            options["dry_run"]
        )

        prefix = _normalize_prefix(
            options.get(
                "prefix"
            )
        )

        threshold = (
            timezone.now()
            - timedelta(
                days=days
            )
        )

        found = 0
        deleted = 0
        errors = 0

        try:

            files = list(
                _iter_storage_files(
                    prefix
                )
            )

        except FileNotFoundError:

            self.stdout.write(
                "No generated storage prefix."
            )

            return

        except Exception as exc:

            raise CommandError(
                "Unable to list storage prefix "
                f"{prefix!r}: {exc}"
            ) from exc


        for storage_name in files:

            try:

                modified = (
                    _modified_time(
                        storage_name
                    )
                )

            except Exception as exc:

                errors += 1

                self.stderr.write(
                    "Metadata error: "
                    f"{storage_name}: {exc}"
                )

                continue


            if modified >= threshold:
                continue


            found += 1

            if dry_run:

                if options.get(
                    "verbosity",
                    1,
                ) >= 2:

                    self.stdout.write(
                        "Candidate: "
                        + storage_name
                    )

                continue


            try:

                default_storage.delete(
                    storage_name
                )

            except Exception as exc:

                errors += 1

                self.stderr.write(
                    "Delete error: "
                    f"{storage_name}: {exc}"
                )

                continue


            deleted += 1


        self.stdout.write(
            f"Prefix: {prefix}"
        )

        self.stdout.write(
            f"Candidates: {found}"
        )

        if dry_run:

            self.stdout.write(
                "DRY RUN: nothing deleted."
            )

        else:

            self.stdout.write(
                f"Deleted: {deleted}"
            )

        if errors:

            self.stdout.write(
                f"Errors: {errors}"
            )
