"""Verify an installed wheel outside the source checkout and test bootstrap."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import venv
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    if not wheel.is_file():
        parser.error(f"Wheel not found: {wheel}")

    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    with tempfile.TemporaryDirectory(prefix="backendpro-wheel-") as temporary:
        root = Path(temporary)
        venv.EnvBuilder(with_pip=True).create(root / "venv")
        executable = root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

        def run(*arguments):
            return subprocess.check_output(
                [str(executable), *arguments], cwd=root, env=environment,
                text=True, timeout=120,
            )

        run("-m", "pip", "install", "--no-index", "--no-deps", str(wheel))
        run(
            "-c",
            "import backendpro; from importlib.metadata import version; "
            "assert backendpro.__version__ == version('backendpro'), 'Runtime version differs from metadata'",
        )
        run("-m", "backendpro.scripts.validate")
        result = json.loads(run(
            "-m", "backendpro.scripts.search", "circuit breaker", "--domain", "pattern", "--json"
        ))
        assert result["count"] > 0, "Installed search returned no results"
        report = json.loads(run("-m", "backendpro.scripts.coverage", "--json"))
        assert report["summary"]["domain_count"] == 34
        assert report["summary"]["total_rows"] > 0
        run(
            "-c",
            "from backendpro.scripts.coverage import _load_targets; "
            "assert _load_targets().get('database'), 'Missing bundled coverage targets'",
        )
        print("Wheel smoke passed: isolated install, search, CSV validation, coverage targets")


if __name__ == "__main__":
    main()
