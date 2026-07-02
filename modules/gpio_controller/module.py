NAME = "GPIO Controller"
KEY = "gpio"

MENU = [
    {
        "label": "Inputs",
        "url": "/inputs",
        "page": "inputs",
    }
]

SERVICES = [
    "showcontroller-gpio.service"
]


def register(app, render_page):
    return
