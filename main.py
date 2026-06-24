import logging
import sys
from ra_tracker.gui import run

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

if __name__ == "__main__":
    run()
