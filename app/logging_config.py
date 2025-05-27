from __future__ import annotations

import logging
import sys
from rich.logging import RichHandler

# Configure root logger only once
def configure_logging() -> None:
    if getattr(configure_logging, "_configured", False):  # idempotent
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=sys.stdout, markup=True)],
    )
    # Quiet noisy libs
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    configure_logging._configured = True


logger = logging.getLogger("polymarket")
