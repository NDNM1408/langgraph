"""Direct tests for PregelLoop._has_untracked_values.

The flag is a precomputed cache of "does this graph have any UntrackedValue
channel", replacing a per-write `any(isinstance(...))` scan over all channels.
These tests pin the flag's value for graphs with and without untracked state.
Observable behavior (untracked values excluded from the persisted snapshot) is
covered by test_send_with_untracked_value in test_pregel.py.
"""

import operator
from typing import Annotated, Any

from typing_extensions import TypedDict

import langgraph.pregel.main as main_mod
from langgraph.channels.untracked_value import UntrackedValue
from langgraph.graph import END, START, StateGraph
from langgraph.pregel._loop import SyncPregelLoop


def _capture_flag(app, input):
    """Run `app` and return the live loop's `_has_untracked_values` flag."""
    captured: list[bool] = []

    class _SpyLoop(SyncPregelLoop):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            captured.append(self._has_untracked_values)

    orig = main_mod.SyncPregelLoop
    main_mod.SyncPregelLoop = _SpyLoop
    try:
        app.invoke(input)
    finally:
        main_mod.SyncPregelLoop = orig
    assert captured, "loop was never instantiated"
    return captured[-1]


def test_flag_false_without_untracked_value() -> None:
    class State(TypedDict):
        x: Annotated[int, operator.add]

    g = StateGraph(State)
    g.add_node("n", lambda s: {"x": 1})
    g.add_edge(START, "n")
    g.add_edge("n", END)

    assert _capture_flag(g.compile(), {"x": 0}) is False


def test_flag_true_with_untracked_value() -> None:
    class State(TypedDict):
        x: Annotated[int, operator.add]
        resource: Annotated[object, UntrackedValue]

    g = StateGraph(State)
    g.add_node("n", lambda s: {"x": 1, "resource": object()})
    g.add_edge(START, "n")
    g.add_edge("n", END)

    assert _capture_flag(g.compile(), {"x": 0, "resource": object()}) is True
