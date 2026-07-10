from typing import List, Dict
from contextvars import ContextVar

_trace_ctx: ContextVar[List[Dict]] = ContextVar("trace", default=None)


def start_trace():
    """Initialize a fresh trace for the current request."""
    _trace_ctx.set([])


def log_step(from_node: str, to_node: str, title: str, desc: str):
    """Record one architectural step in the current request trace."""
    trace = _trace_ctx.get()
    if trace is not None:
        trace.append({
            "from":  from_node,
            "to":    to_node,
            "title": title,
            "desc":  desc
        })


def get_trace() -> List[Dict]:
    """Returns all recorded steps for the current request."""
    return _trace_ctx.get() or []