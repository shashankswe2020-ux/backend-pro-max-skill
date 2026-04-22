"""Pytest configuration: make the `backendpro` package importable without
requiring an editable install. Mirrors the mapping in pyproject.toml."""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = ROOT / "src" / "backend-pro-max"
SCRIPTS_DIR = PKG_DIR / "scripts"

# Expose `core`, `search`, `validate` under the `backendpro.scripts.*`
# namespace by creating in-memory parent packages and loading the modules
# from their on-disk hyphenated path.
sys.path.insert(0, str(SCRIPTS_DIR))  # allows `import core` directly

if "backendpro" not in sys.modules:
    pkg = types.ModuleType("backendpro")
    pkg.__path__ = [str(PKG_DIR)]
    sys.modules["backendpro"] = pkg

if "backendpro.scripts" not in sys.modules:
    sub = types.ModuleType("backendpro.scripts")
    sub.__path__ = [str(SCRIPTS_DIR)]
    sys.modules["backendpro.scripts"] = sub

# Pre-import the submodules under their dotted name so test code can do
# `from backendpro.scripts import core` if it wants to.
for name in ("core", "search", "validate"):
    if f"backendpro.scripts.{name}" not in sys.modules:
        mod = importlib.import_module(name)
        sys.modules[f"backendpro.scripts.{name}"] = mod
