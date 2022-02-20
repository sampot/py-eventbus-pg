import asyncio
import os
from sys import argv
from typing import List
from dotenv import load_dotenv
from cuid import cuid
from py_eventbus_pg.event_bus import EventBus, Event
from py_eventbus_pg.impl.pg_event_bus import PgEventBus


async def producer(event_bus: EventBus) -> None:
    while True:
        await asyncio.sleep(3)
        await event_bus.publish(Event(id=cuid(), type="test"))


async def consumer(event_bus: EventBus, sub_id: str = "test_client") -> None:
    print("Subscription ID: ", sub_id)
    async with event_bus.subscribe(sub_id) as subscriber:
        async for event in subscriber:
            print(f"Received: {event}")


async def main(argv: List[str]) -> None:
    load_dotenv()

    eventbus = PgEventBus(os.environ["DATABASE_URL"])
    await eventbus.start()
    try:
        if len(argv) == 1:
            print("Create a producer.")
            await asyncio.create_task(producer(eventbus))
        else:
            print("Create a consumer.")
            await asyncio.create_task(consumer(eventbus, argv[1]))

    finally:
        await eventbus.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main(argv))
    except KeyboardInterrupt:
        pass
