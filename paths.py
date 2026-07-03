"""Centralized runtime paths.

The runtime data directory defaults to /opt/showcontroller (the layout used on
the Raspberry Pi target) but can be overridden with the SHOWCONTROLLER_DATA_DIR
environment variable. This makes local development and testing possible without
requiring the production directory layout.
"""

import os

DATA_DIR = os.environ.get("SHOWCONTROLLER_DATA_DIR", "/opt/showcontroller")


def data_path(*parts):
    return os.path.join(DATA_DIR, *parts)


GPIO_RELOAD_FILE = data_path("gpio.reload")
