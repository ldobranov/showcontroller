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
    "services": [],
    "runtime": {
        "role": "node",
        "mode": "video",
        "label": "Video",
        "service": "showcontroller-video-node.service",
        "cleanup": [
            "vlc.*--rc-host 127.0.0.1:4212",
            "/opt/showcontroller/modules/video_player/node.py",
            "cec-client",
        ],
    },

    "description": "Video playback node for show media.",
    "version": "1.4.0",
    "apt_packages": [
        "vlc",
        "cec-utils"
    ],
    "installer": "modules.video_player.install",
}
