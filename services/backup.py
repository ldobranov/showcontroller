import json
import os

CONFIG_FILE = "/opt/showcontroller/config.json"


def config_backup_path():
    return CONFIG_FILE


def restore_config_file(uploaded_file):
    content = uploaded_file.read()

    try:
        data = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Uploaded file is not valid JSON.")

    if not isinstance(data, dict):
        raise ValueError("Config must be a JSON object.")

    tmp_file = CONFIG_FILE + ".tmp"
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, CONFIG_FILE)
