CONFIG_FILE = "/opt/showcontroller/config.json"


def config_backup_path():
    return CONFIG_FILE


def restore_config_file(uploaded_file):
    uploaded_file.save(CONFIG_FILE)
