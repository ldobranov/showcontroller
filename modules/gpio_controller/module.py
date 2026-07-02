NAME = "GPIO Controller"
KEY = "gpio"

MENU = [
    {
        "label": "Triggers",
        "url": "/triggers",
        "page": "triggers",
    }
]

SERVICES = [
    "showcontroller-gpio.service"
]


def register(app, render_page):
    from .routes import register_gpio_routes
    register_gpio_routes(app, render_page)
