MODULE = {
    "key": "video",
    "name": "Video Player",
    "enabled_by_default": False,
    "register": "modules.video_player.routes.register_video_routes",
    "menu": [
        {
            "label": "Videos",
            "url": "/videos",
            "page": "videos",
        }
    ],
    "services": [
        "showcontroller-video-node.service"
    ],

    "description": "Video playback node for show media.",
    "version": "1.3.1",
    "apt_packages": [
        "vlc",
        "cec-utils"
    ],
    "installer": "modules.video_player.install",
}
