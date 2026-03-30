import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from pathlib import Path
import sys

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from database import init_db, DB_PATH


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def client():
    """Create a test client with a fresh DB for each test."""
    # Blow away the DB before each test
    if DB_PATH.exists():
        DB_PATH.unlink()
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup after test
    if DB_PATH.exists():
        DB_PATH.unlink()
