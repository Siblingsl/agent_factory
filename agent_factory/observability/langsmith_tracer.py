from __future__ import annotations

from contextlib import contextmanager
import time


@contextmanager
def trace_span(name: str, **attrs):
    started = time.time()
    try:
        yield {"name": name, "attrs": attrs, "started": started}
    finally:
        _ = time.time() - started
