# SPDX-License-Identifier: GPL-3.0-only

try:
    from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
except ImportError as exc:
    if "attempted relative import" not in str(exc):
        raise
    try:
        from nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    except ModuleNotFoundError as module_exc:
        if module_exc.name not in {"node_helpers", "torch"}:
            raise
        NODE_CLASS_MAPPINGS = {}
        NODE_DISPLAY_NAME_MAPPINGS = {}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
