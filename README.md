# py-eventbus-pg

A PoC Python persistent event bus with PostgreSQL.

## Description

Published events are delivered to each subscription at least once and in publishment order. Consumers to the same subscription have to cope with situations such as process crash.

## Get Started

Copy file `sample.env` to `.env`.


## Example code

### Event Consumer

```python
async with event_bus.subscribe(sub_id) as subscriber:
    async for event in subscriber:
        print(f"Received: {event}")

```
