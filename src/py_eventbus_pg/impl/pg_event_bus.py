import asyncio
from contextlib import asynccontextmanager
import hashlib
import struct
from typing import Any, AsyncGenerator, AsyncIterator, List, Optional
import json
import asyncpg
from cuid import cuid
from py_eventbus_pg.event_bus import EventBus, Subscription, Event

EVENTS_CHANNEL = "events"


class PgEventBus(EventBus):
    def __init__(self, db_url: str) -> None:
        super().__init__()

        self.db_url = db_url
        self.conn: asyncpg.Connection = None

    async def start(self) -> None:
        # connect to the database.
        self.conn = await asyncpg.connect(self.db_url)

        # create tables if not existent yet.
        await self.conn.execute(
            """CREATE TABLE IF NOT EXISTS events(
                id VARCHAR(32) PRIMARY KEY,
                type VARCHAR(64) NOT NULL,
                data JSONB
            );
            CREATE TABLE IF NOT EXISTS subscriptions(
                id VARCHAR(32) PRIMARY KEY,
                checkpoint VARCHAR(32) NOT NULL
            );
            """
        )
        print("Event bus started.")

    async def stop(self) -> None:
        if self.conn:
            await self.conn.close()

        print("Event bus stopped.")

    async def publish(self, event: Event) -> None:
        await self.conn.execute(
            """INSERT INTO events VALUES($1, $2, $3)""",
            event.id,
            event.type,
            event.data,
        )

        # notify a new event is ready for processing.
        await self.conn.execute(
            "SELECT pg_notify($1, $2);", EVENTS_CHANNEL, f"{event.id}:{event.type}"
        )

        print(f"Published: {event}")

    @asynccontextmanager
    async def subscribe(self, subcription_id: str) -> AsyncIterator["SubscriptionImpl"]:
        c = await asyncpg.connect(self.db_url)
        try:
            yield SubscriptionImpl(c, subcription_id)
        finally:
            # close the connection and release the lock.
            await c.close()


class SubscriptionImpl(Subscription):
    def __init__(self, conn: asyncpg.Connection, sub_id: str,live:bool = True) -> None:
        super().__init__()

        self.conn = conn
        self.sub_id = sub_id
        self._lock_num: int = self.calc_lock_num()
        self._event_available: asyncio.Event = None
        self._live = live

    async def __aiter__(self) -> Optional[AsyncGenerator]:
        """AsyncGenerator protocol."""
        while True:
            # try to acquire session-level advisory lock
            if not await self.try_lock():
                # if lock not acquired, sleep for 5 seconds, then try again.
                await asyncio.sleep(5)
                continue

            last_seen_id = await self.get_checkpoint()
            while True:
                # deliver until no remaining events.
                events = await self.fetch_events(after_id=last_seen_id)
                if len(events) == 0:
                    # wait for new event available.
                    await self.wait_for_event()
                    continue

                for e in events:
                    yield e

                last_seen_id = events[-1].id
                await self.save_checkpoint(last_seen_id)

    def calc_lock_num(self) -> int:
        """Convert subscription id to a bigint which is need by pg advisory lock."""
        hash = hashlib.sha1(self.sub_id.encode("utf-8"))
        (num,) = struct.unpack("q", hash.digest()[:8])
        return num

    async def fetch_events(
        self, after_id: Optional[str] = None, limit: Optional[int] = 5
    ) -> List[Event]:
        """Fetch a batch of events."""
        res = None
        if after_id:
            res = await self.conn.fetch(
                f"SELECT * FROM events WHERE id>$1 ORDER BY id LIMIT {limit}", after_id
            )
        else:
            res = await self.conn.fetch(
                f"SELECT * FROM events  ORDER BY id LIMIT {limit}"
            )

        results: List[Event] = []

        for item in res:
            results.append(
                Event(
                    id=item["id"],
                    type=item["type"],
                    data=json.loads(item["data"]) if item["data"] else None,
                )
            )
        return results

    async def save_checkpoint(self, value: str) -> None:
        """Upsert the checkpoint value for the subscription."""
        await self.conn.execute(
            """INSERT INTO subscriptions AS sub(id,checkpoint) VALUES($1, $2) ON CONFLICT (id) DO UPDATE SET checkpoint=$2 WHERE sub.id=$1
            """,
            self.sub_id,
            value,
        )

    async def get_checkpoint(self) -> str:
        """Load last processed event id from the database."""
        res = await self.conn.fetchrow(
            "SELECT checkpoint FROM subscriptions WHERE id=$1", self.sub_id
        )

        if not res or len(res) == 0:
            return None
        else:
            return res[0]

    async def try_lock(self) -> bool:
        print("Trying to acquire lock...")
        res = await self.conn.fetchval(
            f"SELECT pg_try_advisory_lock({self._lock_num});"
        )
        print("Lock acquird? ", res)

        return res

    async def release_lock(self) -> None:
        print("Releasing lock...")
        await self.conn.execute(f"select pg_advisory_unlock({self._lock_num});")
        print("Lock released.")

    async def wait_for_event(self) -> None:
        """Wait until event is ready."""
        self._event_available = asyncio.Event()
        await self.conn.add_listener(EVENTS_CHANNEL, self._listener)
        try:
            await self._event_available.wait()
        finally:
            await self.conn.remove_listener(EVENTS_CHANNEL, self._listener)

    async def _listener(self, *args: Any) -> None:
        """Resume event processing if new event published."""
        self._event_available.set()
