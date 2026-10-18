"""Do not release a file while a cancelled request still owns worker I/O."""

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


async def await_owned_io(operation: Coroutine[Any, Any, T]) -> T:
    worker = asyncio.create_task(operation)
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        while not worker.done():
            try:
                await asyncio.shield(worker)
            except asyncio.CancelledError:
                continue
        worker.result()
        raise
