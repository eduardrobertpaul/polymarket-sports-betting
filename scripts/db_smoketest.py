"""
Run `python scripts/db_smoketest.py` to verify the async SQLAlchemy
engine can connect to Postgres and execute a simple SELECT.
"""

import asyncio
import sys
from pathlib import Path
import sqlalchemy as sa

# Add the project root directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.base import engine  # uses settings from .env via app.config


async def main() -> None:
    async with engine.begin() as conn:
        value = await conn.scalar(sa.text("SELECT 42"))
        print("Connected! Got value:", value)


if __name__ == "__main__":
    asyncio.run(main())
