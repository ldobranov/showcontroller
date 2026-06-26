from gpio import run_gpio
from logger import log

if __name__ == "__main__":
    log("GPIO SERVICE STARTED")
    try:
        run_gpio()
    finally:
        log("GPIO SERVICE STOPPED")
