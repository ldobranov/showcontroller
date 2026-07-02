import shutil
import subprocess


def cec_available():
    return shutil.which("cec-client") is not None


def run_cec(commands, log=None, timeout=8):
    if not cec_available():
        if log:
            log("CEC: cec-client not installed")
        return False

    if isinstance(commands, str):
        commands = [commands]

    payload = "\n".join(commands).strip() + "\n"

    try:
        result = subprocess.run(
            ["cec-client", "-s", "-d", "1"],
            input=payload,
            text=True,
            capture_output=True,
            timeout=timeout,
        )

        if log:
            if result.stdout.strip():
                log(f"CEC stdout: {result.stdout.strip()}")
            if result.stderr.strip():
                log(f"CEC stderr: {result.stderr.strip()}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        if log:
            log("CEC: timeout, cec-client killed")
        return False

    except Exception as exc:
        if log:
            log(f"CEC error: {exc}")
        return False


def tv_power_on(log=None):
    if log:
        log("CEC: TV power on + active source")

    return run_cec(
        [
            "on 0",
            "as",
        ],
        log=log,
        timeout=8,
    )


def tv_active_source(log=None):
    if log:
        log("CEC: set active source")

    return run_cec(
        [
            "as",
        ],
        log=log,
        timeout=6,
    )


def tv_scan(log=None):
    if log:
        log("CEC: scan")

    return run_cec(
        [
            "scan",
        ],
        log=log,
        timeout=10,
    )
