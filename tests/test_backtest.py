import pytest
import asyncio

from app.backtest import compute_brier_scores

@pytest.mark.asyncio
async def test_compute_brier_scores_empty(tmp_path, monkeypatch):
    # Patch session factory to use an empty in-mem SQLite DB
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.db.base import async_session_factory, Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    # Import ORM models so Results table is registered
    import app.db.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(
        "app.backtest.async_session_factory",
        async_sessionmaker(engine, expire_on_commit=False),
    )

    scores = await compute_brier_scores()
    assert scores == {}
