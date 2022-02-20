"""The event bus interface.

For events publishing and subscription.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncGenerator, AsyncIterator, Dict, Optional


@dataclass
class Event(object):
    """Encapsulate data of events."""

    id: str
    type: str
    data: Optional[Dict[str, Any]] = None


class EventBus(ABC):
    @abstractmethod
    async def start(self) -> None:
        """Start the event bus."""
        raise NotImplementedError()

    @abstractmethod
    async def stop(self) -> None:
        """Stop the event bus."""
        raise NotImplementedError()

    @abstractmethod
    async def publish(event: Event) -> None:
        """Publish an event."""
        raise NotImplementedError()

    @abstractmethod
    def subscribe(subcription_id: str) -> AsyncIterator["Subscription"]:
        """Create/connect to an subscription with the specified id."""
        raise NotImplementedError()


class Subscription(ABC):
    """Represent a subscription to the event bus."""

    @abstractmethod
    async def __aiter__(self) -> Optional[AsyncGenerator]:
        pass
