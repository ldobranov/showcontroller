NAME = "Video Player"
KEY = "video"

MENU = [
    {
        "label": "Videos",
        "url": "/videos",
        "page": "videos",
    }
]

SERVICES = [
    "showcontroller-video-node.service"
]


def register(app, render_page):
    from .routes import register_video_routes
    register_video_routes(app, render_page)
