MODULE = {
    "key": "gpio",
    "name": "GPIO Controller",
    "enabled_by_default": True,
    "register": "modules.gpio_controller.routes.register_gpio_routes",
    "menu": [
        {
            "label": "Triggers",
            "url": "/triggers",
            "page": "triggers",
        }
    ],
    "services": [],
    "runtime": {
        "role": "node",
        "mode": "gpio",
        "label": "GPIO",
        "service": "showcontroller-gpio.service",
        "cleanup": [],
    },
    "description": "GPIO inputs, triggers and UDP output.",
    "version": "1.3.9",
    "apt_packages": [
        "python3-rpi.gpio"
    ],
    "installer": "modules.gpio_controller.install",
}
