"""Entry point for the RA Tracker desktop application."""

import logging
import sys
from ra_tracker.gui import run

# Set up global logging configuration shared by every module.
# Logs go to stdout with a timestamp and the originating module name.
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

# Only start the Qt application when run directly (``python main.py``),
# not when the package is imported elsewhere.
if __name__ == "__main__":
    run()
