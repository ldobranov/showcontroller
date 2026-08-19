from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from config import load_config


DEFAULT_TIMEOUT_SECONDS = 10


def get_healthchecks_config():
    cfg = load_config()
    healthchecks = cfg.get("healthchecks", {})

    return {
        "enabled": bool(healthchecks.get("enabled", False)),
        "ping_url": str(healthchecks.get("ping_url", "")).strip(),
    }


def is_valid_ping_url(url):
    try:
        parsed = urlparse((url or "").strip())
    except ValueError:
        return False

    return (
        parsed.scheme == "https"
        and parsed.netloc == "hc-ping.com"
        and bool(parsed.path.strip("/"))
    )


def send_heartbeat(timeout=DEFAULT_TIMEOUT_SECONDS):
    settings = get_healthchecks_config()

    if not settings["enabled"]:
        return True, "Healthchecks monitoring is disabled."

    ping_url = settings["ping_url"]

    if not is_valid_ping_url(ping_url):
        return False, "Healthchecks Ping URL is missing or invalid."

    request = Request(
        ping_url,
        method="HEAD",
        headers={"User-Agent": "ShowController Healthcheck"},
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)

            if 200 <= status < 300:
                return True, "Heartbeat sent successfully."

            return False, f"Healthchecks returned HTTP {status}."

    except HTTPError as exc:
        return False, f"Healthchecks returned HTTP {exc.code}."

    except URLError as exc:
        return False, f"Healthchecks is unreachable: {exc.reason}"

    except Exception as exc:
        return False, f"Healthchecks heartbeat failed: {exc}"
        
def main():
    ok, message = send_heartbeat()

    if not ok:
        print(message, flush=True)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
