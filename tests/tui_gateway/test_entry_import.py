"""Entry-point imports use the TUI suite's process-bootstrap fixture."""

import sys


def test_module_imports_cleanly():
    for name in list(sys.modules):
        if name.startswith("tui_gateway"):
            del sys.modules[name]
    import tui_gateway.entry
