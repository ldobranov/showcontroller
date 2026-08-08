import json
import os
import tempfile
import zipfile
from pathlib import Path


BASE_DIR = Path("/opt/showcontroller")

BACKUP_FILES = [
    Path("config.json"),
    Path("modules.json"),
    Path("config/video.json"),
    Path("config/node_mode.json"),
]

OPTIONAL_FILES = [
    Path("config/video_deps_installed"),
]


def config_backup_path():
    tmp = tempfile.NamedTemporaryFile(
        prefix="showcontroller-backup-",
        suffix=".zip",
        delete=False,
    )
    tmp.close()

    backup_path = Path(tmp.name)

    with zipfile.ZipFile(
        backup_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as zf:

        for relative_path in BACKUP_FILES + OPTIONAL_FILES:
            source = BASE_DIR / relative_path

            if source.exists() and source.is_file():
                zf.write(
                    source,
                    arcname=str(relative_path),
                )

    return str(backup_path)


def _validate_json_file(path, data):
    if not isinstance(data, dict):
        raise ValueError(
            f"{path} must contain a JSON object."
        )


def restore_config_file(uploaded_file):
    filename = (
        uploaded_file.filename or ""
    ).lower()

    if not filename.endswith(".zip"):
        raise ValueError(
            "Backup file must be a ZIP archive."
        )

    tmp = tempfile.NamedTemporaryFile(
        suffix=".zip",
        delete=False,
    )

    try:
        uploaded_file.save(tmp.name)
        tmp.close()

        with zipfile.ZipFile(
            tmp.name,
            "r",
        ) as zf:

            names = set(zf.namelist())

            allowed = {
                str(p)
                for p in BACKUP_FILES + OPTIONAL_FILES
            }

            for name in names:
                if name not in allowed:
                    raise ValueError(
                        f"Unexpected file in backup: {name}"
                    )

            for relative_path in BACKUP_FILES:
                name = str(relative_path)

                if name not in names:
                    continue

                content = zf.read(name)

                try:
                    data = json.loads(
                        content.decode("utf-8")
                    )
                except (
                    json.JSONDecodeError,
                    UnicodeDecodeError,
                ):
                    raise ValueError(
                        f"{name} is not valid JSON."
                    )

                _validate_json_file(
                    name,
                    data,
                )

            for relative_path in BACKUP_FILES:
                name = str(relative_path)

                if name not in names:
                    continue

                target = BASE_DIR / relative_path
                target.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                data = json.loads(
                    zf.read(name).decode("utf-8")
                )

                tmp_target = Path(
                    str(target) + ".tmp"
                )

                with open(
                    tmp_target,
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(
                        data,
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )

                os.replace(
                    tmp_target,
                    target,
                )

            for relative_path in OPTIONAL_FILES:
                name = str(relative_path)

                if name not in names:
                    continue

                target = BASE_DIR / relative_path
                target.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                target.write_bytes(
                    zf.read(name)
                )

    except zipfile.BadZipFile:
        raise ValueError(
            "Uploaded file is not a valid ZIP archive."
        )

    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
