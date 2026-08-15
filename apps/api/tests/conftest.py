import pytest

from app.db.session import engine


@pytest.fixture(autouse=True)
async def _dispose_engine_pool_after_each_test():
    """pytest-asyncio hands each test function its own event loop (asyncio_default_fixture_loop_scope
    = function in pytest.ini). app.db.session.engine is a module-level singleton whose connection
    pool otherwise outlives a single test's loop, so a pooled asyncpg connection opened by one test
    gets reused by the next test's *different* loop and blows up with "attached to a different loop".
    Disposing the pool after every test forces the next DB-touching test to open fresh connections
    on its own loop."""
    yield
    await engine.dispose()
