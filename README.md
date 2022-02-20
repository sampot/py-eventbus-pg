# py-eventbus-pg

A PoC Python persistent event bus with PostgreSQL.

## Description

Published events are delivered to each subscription at least once and in published order. Consumers to the same subscription have to cope with situations such as process crash. For example, ensure all operations are idempotent.

## Get Started

### Copy file `sample.env` to `.env`.

```bash
cp example.env .env
```

### Install Poetry

```bash
pip3 install poetry
```

### Install dependencies

```bash
poetry install
```

### Enter Python Virtual Environment

```bash
poetry shell
```

### Start PostgreSQL server

```bash
docker-compose up -d
```

### Start a Producer

```bash
python -m py_eventbus_pg.main
```

### Start a Consumer

```bash
python -m py_eventbus_pg.main test1
```

,where 'test1' is the subscription ID.

## Example code

### Start the Event Bus

```python
from py_eventbus_pg.impl.pg_event_bus import PgEventBus

eventbus = PgEventBus(os.environ["DATABASE_URL"])
await eventbus.start()
```

### Event Publisher

```python
await event_bus.publish(Event(id=cuid(), type="test"))
```

### Event Consumer

```python
async with event_bus.subscribe(sub_id) as subscriber:
    async for event in subscriber:
        print(f"Received: {event}")

```
