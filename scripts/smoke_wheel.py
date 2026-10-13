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
        assert "retrieval" not in result, "Default BM25 result shape changed"
        fallback = json.loads(run(
            "-m", "backendpro.scripts.search", "circuit breaker", "--domain", "pattern",
            "--engine", "hybrid", "--rerank", "--candidate-pool", "20", "--compact",
        ))
        assert fallback["count"] > 0
        assert fallback["retrieval"]["effective_engine"] == "bm25"
        assert fallback["retrieval"]["rerank_requested"] and not fallback["retrieval"]["rerank_applied"]
        assert len(fallback["retrieval"]["fallbacks"]) == 2
        versioned_text = run(
            "-m", "backendpro.scripts.search", "pydantic dictionary", "--stack", "python-fastapi",
            "--evidence", "--library-version", "pydantic=2.10.6",
        )
        versioned = json.loads(versioned_text)
        assert len(versioned_text.rstrip("\n")) <= 6000
        assert versioned["results"][0]["version_match"] == "match"
        detail = json.loads(run(
            "-m", "backendpro.scripts.search", "--evidence-id", versioned["results"][0]["id"],
        ))
        assert detail["id"] == versioned["results"][0]["id"]
        project = root / "project"
        project.mkdir()
        (project / "sample.py").write_text("def retry(attempts):\n    return attempts\n", encoding="utf-8")
        for arguments in (
            ["init", "-q"], ["add", "sample.py"],
            ["-c", "user.name=Wheel Test", "-c", "user.email=test@example.invalid",
             "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "Fixture",
             "-m", "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"],
        ):
            subprocess.run(["git", "-C", str(project), *arguments], check=True, capture_output=True, timeout=30)
        local_text = run(
            "-m", "backendpro.scripts.search", "context", "retry",
            "--workspace-root", str(project), "--paths", "sample.py",
        )
        local = json.loads(local_text)
        assert local["count"] == 1 and local["results"][0]["kind"] == "local"
        assert len(local_text.rstrip("\n")) <= 6000
        store = root / "memory"
        store.mkdir(mode=0o700)
        memory = json.loads(run(
            "-m", "backendpro.scripts.search", "memory", "init",
            "--workspace-root", str(project), "--store", str(store),
        ))
        assert memory["records"] == 0 and not memory["reuse_enabled"]
        report = json.loads(run("-m", "backendpro.scripts.coverage", "--json"))
        assert report["summary"]["domain_count"] == 34
        assert report["summary"]["total_rows"] > 0
        run(
            "-c",
            "from backendpro.scripts.coverage import _load_targets; "
            "assert _load_targets().get('database'), 'Missing bundled coverage targets'",
        )
        print("Wheel smoke passed: isolated install, BM25 defaults, explicit fallback, P2 evidence/detail, P3 local context, P4 disabled memory, source validation, coverage targets")


if __name__ == "__main__":
    main()
