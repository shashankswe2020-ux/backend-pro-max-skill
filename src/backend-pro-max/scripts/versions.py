"""Conservative, local-only Python dependency observations (not an environment solver)."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

_VERSION = r"\d+(?:\.\d+){0,3}"
_CLAUSE = re.compile(rf"(==|>=|<=|>|<)\s*({_VERSION})")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_REQUIREMENT = re.compile(r"([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]+\])?\s*(.*)")


def normalize_name(name: str) -> str:
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise ValueError("Invalid library identity")
    return re.sub(r"[-_.]+", "-", name).lower()


def _number(value: str) -> tuple:
    parts = tuple(int(part) for part in value.split("."))
    return parts + (0,) * (4 - len(parts))


def interval(specifier: str) -> tuple:
    """Numeric release intervals only; unsupported PEP 440 constructs stay unknown."""
    if not isinstance(specifier, str) or not specifier.strip():
        raise ValueError("A numeric version constraint is required")
    lower, upper = ((0, 0, 0, 0), True), (None, False)
    for clause in specifier.split(","):
        match = _CLAUSE.fullmatch(clause.strip())
        if not match:
            raise ValueError("Unsupported version constraint; use numeric ==, >=, >, <=, < clauses")
        operator, value = match.groups()
        number = _number(value)
        if operator in ("==", ">=", ">"):
            candidate = (number, operator != ">")
            if candidate[0] > lower[0] or (candidate[0] == lower[0] and not candidate[1]):
                lower = candidate
        if operator in ("==", "<=", "<"):
            candidate = (number, operator != "<")
            if upper[0] is None or candidate[0] < upper[0] or (candidate[0] == upper[0] and not candidate[1]):
                upper = candidate
    return lower, upper


def _intersection(intervals: list) -> tuple:
    lower = max((item[0] for item in intervals), key=lambda bound: (bound[0], not bound[1]))
    upper = min(
        (item[1] for item in intervals if item[1][0] is not None),
        key=lambda bound: (bound[0], bound[1]), default=(None, False),
    )
    return lower, upper


def _empty(bounds: tuple) -> bool:
    low, high = bounds
    return high[0] is not None and (low[0] > high[0] or (low[0] == high[0] and not (low[1] and high[1])))


def version_match(specifier: str, observation: dict) -> str:
    if observation.get("status") == "conflict":
        return "conflict"
    if observation.get("status") not in ("resolved", "constrained"):
        return "unknown"
    wanted = interval(specifier)
    actual = _intersection([interval(item["specifier"]) for item in observation["observations"]])
    common = _intersection([wanted, actual])
    if _empty(common):
        return "mismatch"
    return "match" if common == actual else "unknown"


def resolve_versions(project_path: str | None = None, library_versions: dict | None = None) -> dict:
    """Read only named root manifests; never execute tooling, recurse, or access a network."""
    observations: dict[str, list] = {}
    source_hashes = {}
    issues = []

    def add(name, specifier, source):
        name = normalize_name(name)
        if specifier == "*":
            specifier = ">=0"
        try:
            interval(specifier)
        except ValueError:
            specifier = None
        observation = {"source": source, "specifier": specifier}
        if source in source_hashes:
            observation["source_sha256"] = source_hashes[source]
        observations.setdefault(name, []).append(observation)

    if library_versions is not None:
        if not isinstance(library_versions, dict):
            raise ValueError("library_versions must be an object of numeric release versions")
        seen = set()
        for name, value in library_versions.items():
            name = normalize_name(name)
            if name in seen or not isinstance(value, str) or not re.fullmatch(_VERSION, value):
                raise ValueError("Explicit library versions must be unique numeric release versions")
            seen.add(name)
            add(name, "==" + value, "explicit")

    def requirement(text, source):
        if not isinstance(text, str):
            raise ValueError(f"Invalid dependency entry in {source}")
        text = text.split(" #", 1)[0].strip()
        if not text or text.startswith("#"):
            return
        match = _REQUIREMENT.fullmatch(text)
        if not match:
            issues.append(f"{source}: unsupported directive or dependency; included files are not followed")
            return
        name, specifier = match.groups()
        add(name, specifier or ">=0", source)

    if project_path is not None:
        root = Path(project_path).resolve()
        if not root.is_dir():
            raise ValueError("project_path must be an existing directory")
        for filename in ("requirements.txt", "pyproject.toml", "uv.lock", "poetry.lock", "Pipfile.lock", ".python-version"):
            path = root / filename
            if not path.exists() and not path.is_symlink():
                continue
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
                raise ValueError(f"{filename}: expected a regular non-symlink file of at most 2 MB")
            content = path.read_bytes()
            source_hashes[filename] = hashlib.sha256(content).hexdigest()
            text = content.decode("utf-8")
            if filename == "requirements.txt":
                for line in text.splitlines():
                    requirement(line, filename)
            elif filename == ".python-version":
                release = text.strip()
                if re.fullmatch(r"\d+(?:\.\d+)?", release):
                    upper = release.split(".")
                    upper[-1] = str(int(upper[-1]) + 1)
                    spec = ">=" + release + ",<" + ".".join(upper)
                else:
                    spec = "==" + release
                add("python", spec, filename)
            elif filename == "Pipfile.lock":
                try:
                    document = json.loads(text)
                    for section in ("default", "develop"):
                        for name, entry in document.get(section, {}).items():
                            spec = entry.get("version") if section == "default" and not entry.get("markers") else None
                            add(name, spec, filename)
                except (ValueError, AttributeError, TypeError) as error:
                    raise ValueError(f"Invalid {filename}") from error
            else:
                try:
                    import tomllib
                except ImportError:
                    issues.append(f"{filename}: TOML inspection requires Python 3.11+; no version inferred")
                    continue
                try:
                    document = tomllib.loads(text)
                    if filename == "pyproject.toml":
                        project = document.get("project", {})
                        for dependency in project.get("dependencies", []):
                            requirement(dependency, filename)
                        if project.get("requires-python"):
                            add("python", project["requires-python"], filename)
                        poetry = document.get("tool", {}).get("poetry", {}).get("dependencies", {})
                        for name, spec in poetry.items():
                            add(name, spec if isinstance(spec, str) else None, filename)
                        if "dependencies" in project.get("dynamic", []):
                            issues.append(f"{filename}: dynamic dependencies are not evaluated")
                    else:
                        for entry in document.get("package", []):
                            spec = "==" + entry["version"] if entry.get("version") else None
                            if entry.get("marker") or entry.get("markers") or entry.get("resolution-markers"):
                                spec = None
                            add(entry["name"], spec, filename)
                except (ValueError, KeyError, AttributeError, TypeError) as error:
                    raise ValueError(f"Invalid {filename}") from error

    result = {}
    for name, entries in sorted(observations.items()):
        known = [interval(entry["specifier"]) for entry in entries if entry["specifier"] is not None]
        bounds = _intersection(known) if known else None
        if bounds is not None and _empty(bounds):
            status = "conflict"
        elif issues or len(known) != len(entries):
            status = "unknown"
        elif bounds is not None and bounds[0][0] == bounds[1][0]:
            status = "resolved"
        else:
            status = "constrained"
        result[name] = {"status": status, "observations": entries}
    return {"libraries": result, "issues": sorted(set(issues))}
