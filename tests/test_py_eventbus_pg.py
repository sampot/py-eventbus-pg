import asyncpg
from dotenv import load_dotenv
import os
import pytest
import pytest_asyncio
import json
from cuid import cuid
from py_eventbus_pg.impl.pg_event_bus import PgEventBus, SubscriptionImpl
from py_eventbus_pg.event_bus import Event

load_dotenv()


@pytest_asyncio.fixture
async def eventbus() -> PgEventBus:
    eventbus = PgEventBus(os.environ["DATABASE_URL"])
    await eventbus.start()
    yield eventbus
    await eventbus.stop()


@pytest_asyncio.fixture
async def connection() -> asyncpg.Connection:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        yield conn
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_publish_event(eventbus: PgEventBus):
    data = json.dumps(dict())
    await eventbus.publish(Event(id=cuid(), type="test_event", data=data))


@pytest.mark.asyncio
async def test_save_checkpoint(eventbus: PgEventBus, connection: asyncpg.Connection):
    sub = SubscriptionImpl(connection, "test_client")
    await sub.save_checkpoint("test_value2")
    value = await sub.get_checkpoint()
    print(f"Checkpoint value: {value}")
    assert value == "test_value2"


@pytest.mark.asyncio
async def test_fetch_events(eventbus: PgEventBus, connection: asyncpg.Connection):
    """Assumed there are more than 10 events already exist."""
    sub = SubscriptionImpl(connection, "test_client")
    events = await sub.fetch_events()
    print(events)

    assert 0 < len(events) <= 5

    after_id = events[-1].id

    events2 = await sub.fetch_events(after_id=after_id)
    print("events2: ", events2)
    assert 0 < len(events) <= 5
    after_id_2 = events2[-1].id

    assert after_id_2 > after_id
