"""Freeze and validate the draft M3 suite offline; never call paid providers."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import random
import runpy
import statistics
import subprocess
import sys
import time
from collections import Counter
from itertools import combinations
from pathlib import Path
from textwrap import indent

from backendpro.scripts.gen_tools_schema import TOOLS, generate
from backendpro.scripts.retrieval_evidence import describe_payload
from jsonschema import ValidationError, validate

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "benchmarks/m3"
ARMS = ("baseline", "context7", "backendpro", "both")
TRACKS = ("backend", "framework", "mixed", "control")
PROVIDERS = {
    "baseline": set(), "context7": {"context7"}, "backendpro": {"backendpro"},
    "both": {"context7", "backendpro"},
}
CONTRACTS = {tool["name"]: tool for tool in TOOLS}
SEED = "backendpro-context7-m3-v1"
MAX_CANDIDATE_BYTES = 65536


def encode(value) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_new(path: Path, value) -> None:
    with path.open("xb") as stream:
        stream.write(encode(value))


def docker(*args, timeout=30, data=None) -> str:
    result = subprocess.run(
        ["docker", *args], input=data, capture_output=True, timeout=timeout, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Docker {args[0]} failed: {result.stderr.decode(errors='replace')[-4000:]}")
    return result.stdout.decode()


def protocol(policy: str, tasks: list[dict], model: str | None = None, repetitions: int = 3) -> dict:
    if policy not in ("optional", "required"):
        raise ValueError("Policy must be optional or required")
    if type(repetitions) is not int or repetitions not in (1, 3):
        raise ValueError("Repetitions must be one exploratory run or three planned repetitions")
    return {
        "id": f"{SEED}-{policy}", "retrieval_policy": policy, "seed": SEED,
        "status": "draft_frozen_not_reviewed", "model": model,
        "arms": list(ARMS), "task_ids": [task["id"] for task in tasks], "repetitions": repetitions,
        "limits": {
            "retrieval_calls": 3, "response_characters": 6000, "candidate_bytes": MAX_CANDIDATE_BYTES,
            "model_turns": 16, "output_tokens_per_turn": 2048, "generation_seconds": 600,
            "grading_seconds": 15, "grading_memory": "512m", "grading_cpus": 1,
        },
        "retrieval_allocation": (
            "Single-source arms share the same three-call total as both. In required mode, reserve "
            "one call for each as-yet unattempted source. Errors and empty responses consume calls."
        ),
        "required_boundary": "Before first shell or finish, including repository inspection.",
        "model_settings": "Must be locked with the selected model before any generation; identical in all arms.",
        "pricing_and_budget": "Pending new explicit approval; previous pilot approval is not reused.",
        "primary_outcome": f"Mean task solve fraction across {repetitions} repetition(s), all assigned tasks retained.",
        "practical_effect_threshold_percentage_points": 10,
        "analysis": {
            "unit": "task cluster, not independent repetitions",
            "primary_pairs": ["_vs_".join(pair) for pair in combinations(ARMS, 2)],
            "confidence": "95% paired task-cluster percentile bootstrap; 5000 draws",
            "p_values": "Paired cluster sign-flip Monte Carlo test; 10000 draws, plus-one correction",
            "multiplicity": "Holm over six overall pairs within each policy; tracks descriptive only",
            "cross_policy_comparisons": "Descriptive only; no combined winner test",
        },
        "review": {
            "tasks": "pending independent reviewer",
            "source_urls": "pending version-specific verification",
            "evidence_application": "pending source-checked review of model-visible output and patch",
            "non_executable_answers": "Not scored in v1; adding design tasks requires two blinded reviewers and adjudication.",
        },
        "limitations": [
            "Author-created small Python suite, not an established industry benchmark.",
            "All tasks and reference implementations are public; held-out status is not claimed.",
            "Framework coverage is limited to Pydantic, Starlette, and HTTPX at pinned versions.",
            "Context7's live index cannot be pinned exactly; retain permitted responses, timestamps, and hashes.",
            "This offline tool does not execute or certify a model client or authorize provider spending.",
        ],
    }


def assignments(tasks: list[dict], repeats: int = 3) -> list[dict]:
    result = []
    for repeat in range(1, repeats + 1):
        ordered = sorted(tasks, key=lambda task: sha(f"{SEED}:{repeat}:{task['id']}".encode()))
        for index, task in enumerate(ordered):
            offset = (index + repeat - 1) % len(ARMS)
            for arm in ARMS[offset:] + ARMS[:offset]:
                result.append({
                    "id": f"{task['id']}.{arm}.r{repeat}", "task_id": task["id"],
                    "track": task["track"], "arm": arm, "repeat": repeat,
                })
    return result


def grader_source(checks: str) -> str:
    return (
        "import importlib.util, io, json, sys, unittest\n"
        "class Contract(unittest.TestCase):\n"
        "    def test_contract(self):\n"
        "        spec = importlib.util.spec_from_file_location('solution', '/tmp/solution.py')\n"
        "        s = importlib.util.module_from_spec(spec)\n"
        "        sys.modules['solution'] = s\n"
        "        spec.loader.exec_module(s)\n"
        + indent(checks, "        ")
        + "\nstream = io.StringIO()\n"
        "result = unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.loadTestsFromTestCase(Contract))\n"
        "print('M3_RESULT ' + json.dumps({'passed': result.wasSuccessful(), 'ran': result.testsRun, "
        "'failures': len(result.failures), 'errors': len(result.errors), 'diagnostic': stream.getvalue()[-8000:]}))\n"
        "sys.exit(0 if result.wasSuccessful() else 1)\n"
    )


def freeze(output: Path, image: str, model: str | None = None, repetitions: int = 3) -> dict:
    if output.exists():
        raise ValueError("Frozen output already exists")
    protocol("required", [], model, repetitions)
    tasks = runpy.run_path(str(SOURCE / "tasks.py"))["TASKS"]
    if len(tasks) != 24 or len({task["id"] for task in tasks}) != 24:
        raise ValueError("Expected 24 unique tasks")
    if Counter(task["track"] for task in tasks) != dict.fromkeys(TRACKS, 6):
        raise ValueError("Expected six tasks in each track")
    info = json.loads(docker("image", "inspect", image))[0]
    if info["Os"] != "linux" or info["Architecture"] not in ("arm64", "amd64"):
        raise ValueError("Expected a supported Linux grading image")
    versions = json.loads(docker(
        "run", "--rm", "--network", "none", "--entrypoint", "python", info["Id"], "-c",
        "import json, platform, importlib.metadata as m; "
        "print(json.dumps({'python':platform.python_version(),'packages':{d.metadata['Name']:d.version for d in m.distributions()}}))",
    ))
    required = {"pydantic": "2.14.0", "starlette": "1.7.0", "httpx": "0.28.1"}
    if versions["python"] != "3.12.13" or any(versions["packages"].get(k) != v for k, v in required.items()):
        raise ValueError("Grading image does not match the pinned framework/Python versions")
    output.mkdir(parents=True)
    metadata = []
    for task in tasks:
        public = output / "agent" / task["id"]
        private = output / "grading" / task["id"]
        public.mkdir(parents=True)
        private.mkdir(parents=True)
        (public / "solution.py").write_text(task["starter"])
        write_new(public / "task.json", {
            "id": task["id"], "problem": task["problem"], "entrypoint": "solution.py",
            "environment": versions,
        })
        (private / "reference.py").write_text(task["reference"])
        (private / "check.py").write_text(grader_source(task["checks"]))
        metadata.append({key: task[key] for key in ("id", "track", "source_urls", "review_status")})
    for policy in ("optional", "required"):
        write_new(output / f"{policy}.protocol.json", protocol(policy, metadata, model, repetitions))
    write_new(output / "assignments.json", assignments(metadata, repetitions))
    write_new(output / "tools.json", generate())
    manifest = {
        "status": "frozen_not_reviewed_not_run", "tasks": metadata,
        "image_id": info["Id"], "architecture": info["Architecture"], "environment": versions,
        "files": {str(path.relative_to(output)): sha(path.read_bytes())
                  for path in sorted(output.rglob("*")) if path.is_file()},
        "source_sha256": {
            str(path.relative_to(ROOT)): sha(path.read_bytes())
            for path in [SOURCE / "tasks.py", SOURCE / "environment/Dockerfile",
                         SOURCE / "environment/requirements.txt", Path(__file__),
                         ROOT / "scripts/report_swebench_comparison.py",
                         *sorted((ROOT / "src/backend-pro-max").rglob("*.py")),
                         *sorted((ROOT / "src/backend-pro-max/data").rglob("*.csv")),
                         ROOT / ".claude/skills/backend-pro-max/SKILL.md",
                         ROOT / "src/backend-pro-max/templates/base/SKILL.md",
                         ROOT / "src/backend-pro-max/templates/base/skill-content.md"]
        },
        "model_runs": 0, "paid_generation_authorized": False,
    }
    write_new(output / "manifest.json", manifest)
    return manifest


def load_frozen(root: Path) -> dict:
    value = json.loads((root / "manifest.json").read_bytes())
    for name, expected in value["files"].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
            raise ValueError("Invalid frozen artifact path")
        if sha(path.read_bytes()) != expected:
            raise ValueError(f"Frozen artifact changed: {name}")
    return value


class RetrievalWorkflow:
    """Enforce treatment before an external client executes shell or finish."""

    def __init__(self, policy: str, arm: str, contracts: dict | None = None):
        if policy not in ("optional", "required") or arm not in ARMS:
            raise ValueError("Unknown treatment")
        self.policy, self.arm = policy, arm
        self.contracts = CONTRACTS if contracts is None else contracts
        self.attempted = set()
        self.events = []
        self.calls = 0
        self.finished = False

    def guard(self, action: str) -> None:
        if action not in ("shell", "finish") or self.finished:
            raise ValueError("Invalid action or action after finish")
        missing = PROVIDERS[self.arm] - self.attempted
        if self.policy == "required" and action in ("shell", "finish") and missing:
            raise ValueError(f"Retrieve before {action}; missing sources: {', '.join(sorted(missing))}")
        if action == "finish":
            self.finished = True

    def retrieve(self, name: str, arguments: dict, invoke, transport: str) -> dict:
        if self.finished:
            raise ValueError("Retrieval after finish is invalid")
        provider = "backendpro" if name in self.contracts else "context7" if name == "context7" else None
        if provider not in PROVIDERS[self.arm]:
            raise ValueError("Knowledge tool is unavailable in this arm")
        if self.calls >= 3:
            raise ValueError("Shared three-call retrieval limit reached")
        missing = PROVIDERS[self.arm] - self.attempted
        if self.policy == "required" and provider not in missing and 3 - self.calls <= len(missing):
            raise ValueError("Remaining calls are reserved for the other required source")
        schema = self.contracts[name]["parameters"] if provider == "backendpro" else {
            "type": "object", "properties": {"query": {"type": "string", "minLength": 1, "maxLength": 500}},
            "required": ["query"], "additionalProperties": False,
        }
        try:
            validate(arguments, schema)
        except ValidationError as error:
            raise ValueError(f"Invalid tool arguments: {error.message}") from error
        if transport not in ("mcp_stdio", "context7_search_api", "offline_fixture"):
            raise ValueError("Explicit supported transport required")
        if transport != "offline_fixture" and transport != (
            "mcp_stdio" if provider == "backendpro" else "context7_search_api"
        ):
            raise ValueError("Transport does not match the provider")
        self.calls += 1
        self.attempted.add(provider)
        started = time.monotonic()
        event = {"name": name, "provider": provider, "arguments": arguments, "transport": transport}
        try:
            value = invoke(name, arguments)
            evidence = describe_payload(value)
        except (OSError, RuntimeError, ValueError, TypeError) as error:
            value = {"error": str(error)}
            evidence = {"status": "error", "result_count": None, "evidence_ids": [], "citations": []}
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        visible = value
        if len(raw) > 6000:
            visible = {"truncated": True, "payload_sha256": sha(raw.encode()), "excerpt": ""}
            lo, hi = 0, len(raw)
            while lo < hi:
                middle = (lo + hi + 1) // 2
                visible["excerpt"] = raw[:middle]
                if len(json.dumps(visible, ensure_ascii=False, separators=(",", ":"))) <= 6000:
                    lo = middle
                else:
                    hi = middle - 1
            visible["excerpt"] = raw[:lo]
        output = json.dumps(visible, ensure_ascii=False, separators=(",", ":"))
        event.update(
            payload=value, payload_sha256=sha(raw.encode()), output=output, output_sha256=sha(output.encode()),
            evidence=evidence, seconds=time.monotonic() - started, truncated=len(raw) > 6000,
            relevance="not_reviewed", application="not_reviewed",
        )
        self.events.append(event)
        return event


def backendpro_mcp(name: str, arguments: dict) -> dict:
    """Actual local stdio adapter; no Context7 or model requests."""
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def call():
        parameters = StdioServerParameters(
            command=sys.executable, args=["-m", "backendpro.scripts.mcp_server"],
        )
        with anyio.fail_after(30):
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    listed = {tool.name: tool for tool in (await session.list_tools()).tools}
                    if set(listed) != set(CONTRACTS) or any(
                        listed[key].inputSchema != contract["parameters"] for key, contract in CONTRACTS.items()
                    ):
                        raise ValueError("Installed MCP contract drift")
                    result = await session.call_tool(name, arguments)
                    if result.isError:
                        raise RuntimeError(result.content[0].text)
                    return json.loads(result.content[0].text)

    return anyio.run(call)


def replay(policy: str, arm: str, actions: list[dict], real_backendpro: bool = False) -> dict:
    """Exercise the real gate with explicit fixtures, never provider requests."""
    workflow = RetrievalWorkflow(policy, arm)
    trace = []
    finished = False
    for action in actions:
        if finished:
            raise ValueError("Actions after finish are invalid")
        name = action["name"]
        try:
            if name in ("shell", "finish"):
                workflow.guard(name)
                finished = name == "finish"
                trace.append({"name": name, "status": "allowed", "executed": False})
            else:
                actual = real_backendpro and name in CONTRACTS
                if actual and "fixture" in action:
                    raise ValueError("Do not mix an actual BackendPro call with a fixture")
                if not actual and not isinstance(action.get("fixture"), dict):
                    raise ValueError("Offline Context7/retrieval needs an explicit fixture object")
                event = workflow.retrieve(
                    name, action.get("arguments", {}),
                    backendpro_mcp if actual else lambda *_, value=action["fixture"]: value,
                    "mcp_stdio" if actual else "offline_fixture",
                )
                trace.append({"name": name, "status": "attempted", "event": event})
        except ValueError as error:
            trace.append({"name": name, "status": "rejected", "error": str(error)})
    return {
        "status": "offline_replay_not_model_execution", "policy": policy, "arm": arm,
        "finished": finished, "retrieval_calls": workflow.calls, "trace": trace,
    }


def grade(root: Path, task_id: str, candidate: Path) -> dict:
    manifest = load_frozen(root)
    if task_id not in {task["id"] for task in manifest["tasks"]}:
        raise ValueError("Unknown task")
    source = candidate.read_bytes()
    if len(source) > MAX_CANDIDATE_BYTES:
        raise ValueError("Candidate exceeds the equal source-size limit")
    tests = (root / "grading" / task_id / "check.py").read_bytes()
    bootstrap = (
        "import base64, pathlib, sys; "
        "pathlib.Path('/tmp/solution.py').write_bytes(base64.b64decode(sys.argv[1])); "
        "exec(compile(base64.b64decode(sys.argv[2]), '/grading/check.py', 'exec'))"
    )
    container = docker(
        "create", "--network", "none", "--memory", "512m", "--cpus", "1", "--pids-limit", "64",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
        "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--log-driver", "json-file", "--log-opt", "max-size=1m", "--log-opt", "max-file=1",
        "--user", "65534:65534", "--workdir", "/work",
        manifest["image_id"], "python", "-I", "-c", bootstrap,
        base64.b64encode(source).decode(), base64.b64encode(tests).decode(),
    ).strip()
    started = time.monotonic()
    timeout = False
    try:
        docker("start", container)
        try:
            exit_code = int(docker("wait", container, timeout=15).strip())
        except subprocess.TimeoutExpired:
            timeout, exit_code = True, None
        logs = subprocess.run(
            ["docker", "logs", "--tail", "50", container], capture_output=True, timeout=15, check=True,
        )
        text = (logs.stdout + logs.stderr).decode(errors="replace")[-24000:]
        reports = [line.removeprefix("M3_RESULT ") for line in text.splitlines() if line.startswith("M3_RESULT ")]
        result = None
        if not timeout and len(reports) == 1:
            try:
                result = json.loads(reports[0])
            except json.JSONDecodeError:
                result = None
        valid = (
            isinstance(result, dict) and result.get("ran") == 1
            and type(result.get("passed")) is bool
            and type(result.get("errors")) is int and type(result.get("failures")) is int
            and result["passed"] == (result["errors"] == result["failures"] == 0)
            and exit_code == (0 if result["passed"] else 1)
        )
        status = "timeout" if timeout else "invalid_report" if not valid else "passed" if result["passed"] else "failed"
        return {
            "task_id": task_id, "status": status, "passed": status == "passed",
            "suite_sha256": sha((root / "manifest.json").read_bytes()),
            "candidate_sha256": sha(source), "grader_sha256": sha(tests),
            "image_id": manifest["image_id"], "seconds": time.monotonic() - started,
            "exit_code": exit_code, "test_report": result if valid else None, "log_tail": text,
        }
    finally:
        docker("rm", "-f", container)


def self_test(root: Path, output: Path) -> dict:
    manifest = load_frozen(root)
    if output.exists():
        raise ValueError("Self-test output already exists")
    output.mkdir(parents=True)
    results = []
    for task in manifest["tasks"]:
        for kind, candidate in (
            ("reference", root / "grading" / task["id"] / "reference.py"),
            ("starter", root / "agent" / task["id"] / "solution.py"),
        ):
            result = grade(root, task["id"], candidate)
            result["kind"] = kind
            write_new(output / f"{task['id']}.{kind}.json", result)
            results.append(result)
            print(task["id"], kind, result["status"], flush=True)
    passed = all(
        row["status"] == ("passed" if row["kind"] == "reference" else "failed")
        for row in results
    )
    report = {
        "status": "passed" if passed else "failed",
        "purpose": "Reference/starter infrastructure validation, not model or retrieval comparison",
        "suite_sha256": sha((root / "manifest.json").read_bytes()),
        "reference_passed": sum(row["kind"] == "reference" and row["passed"] for row in results),
        "starter_failed": sum(row["kind"] == "starter" and row["status"] == "failed" for row in results),
        "model_attempts": 0, "independent_review": "pending",
        "artifacts": {path.name: sha(path.read_bytes()) for path in sorted(output.glob("*.json"))},
    }
    write_new(output / "summary.json", report)
    return report


def clustered_pair(left: dict[str, float], right: dict[str, float], seed: str) -> dict:
    if not left or left.keys() != right.keys():
        raise ValueError("Paired task clusters must be identical and nonempty")
    deltas = [left[key] - right[key] for key in sorted(left)]
    rng = random.Random(seed)
    observed = statistics.mean(deltas)
    samples = sorted(statistics.mean(rng.choices(deltas, k=len(deltas))) for _ in range(5000))
    extreme = sum(
        abs(statistics.mean(value * rng.choice((-1, 1)) for value in deltas)) >= abs(observed) - 1e-12
        for _ in range(10000)
    )
    return {
        "task_clusters": len(deltas), "difference_percentage_points": observed * 100,
        "bootstrap_95_percentage_points": [samples[124] * 100, samples[4874] * 100],
        "sign_flip_p_unadjusted": (extreme + 1) / 10001,
    }


def holm(pairs: dict) -> None:
    previous = 0.0
    ordered = sorted(pairs, key=lambda key: pairs[key]["sign_flip_p_unadjusted"])
    for index, key in enumerate(ordered):
        adjusted = min(1.0, max(previous, (len(ordered) - index) * pairs[key]["sign_flip_p_unadjusted"]))
        pairs[key]["holm_p"] = adjusted
        previous = adjusted


def report(root: Path, observations: Path, policy: str) -> dict:
    manifest = load_frozen(root)
    frozen_contracts = {
        tool["function"]["name"]: tool["function"]
        for tool in json.loads((root / "tools.json").read_bytes())["openai"]
    }
    if policy not in ("optional", "required"):
        raise ValueError("Unknown policy")
    supplied = json.loads(observations.read_bytes())
    if supplied["protocol_sha256"] != sha((root / f"{policy}.protocol.json").read_bytes()):
        raise ValueError("Observations do not match the separately frozen protocol")
    expected = {row["id"]: row for row in json.loads((root / "assignments.json").read_bytes())}
    seen = {}
    for row in supplied["attempts"]:
        if row["id"] not in expected or row["id"] in seen:
            raise ValueError("Duplicate or unassigned attempt; best-of-N is not allowed")
        if row.get("status") not in ("completed", "budget_limit", "time_limit", "client_error", "not_started"):
            raise ValueError("Unknown generation status")
        for field in ("cost_micro_usd", "input_tokens", "output_tokens", "generation_seconds"):
            kinds = (int, float) if field == "generation_seconds" else (int,)
            if type(row.get(field)) not in kinds or row[field] < 0 or not math.isfinite(row[field]):
                raise ValueError(f"Missing or invalid measurement: {field}")
        identity = expected[row["id"]]
        if row.get("grade_file") is not None:
            path = observations.parent / row["grade_file"]
            if path.name != row["grade_file"] or path.is_symlink() or sha(path.read_bytes()) != row["grade_sha256"]:
                raise ValueError("Grade artifact path/hash mismatch")
            evidence = json.loads(path.read_bytes())
            if (
                evidence["task_id"] != identity["task_id"]
                or evidence["suite_sha256"] != sha((root / "manifest.json").read_bytes())
                or evidence["candidate_sha256"] != row["candidate_sha256"]
                or evidence["image_id"] != manifest["image_id"]
                or evidence["grader_sha256"] != manifest["files"][f"grading/{identity['task_id']}/check.py"]
                or evidence.get("status") not in ("passed", "failed", "timeout", "invalid_report")
            ):
                raise ValueError("Grade does not match the assigned task, candidate, or environment")
            passed = evidence["status"] == "passed"
            if type(evidence.get("passed")) is not bool or evidence["passed"] != passed:
                raise ValueError("Grade status disagrees with its passed flag")
            if evidence["status"] in ("passed", "failed"):
                tests = evidence.get("test_report")
                if (
                    not isinstance(tests, dict) or tests.get("ran") != 1
                    or type(tests.get("passed")) is not bool or tests["passed"] != passed
                    or type(tests.get("failures")) is not int or type(tests.get("errors")) is not int
                    or tests["failures"] < 0 or tests["errors"] < 0
                    or (tests["failures"] == tests["errors"] == 0) != passed
                    or evidence.get("exit_code") != (0 if passed else 1)
                ):
                    raise ValueError("Grade test report is inconsistent")
            evaluation_status = evidence["status"]
        else:
            if row["status"] == "completed":
                raise ValueError("Completed attempt is missing its grade")
            passed = False
            evaluation_status = "not_graded"
        if not isinstance(row.get("trace"), list):
            raise ValueError("Each attempt must retain its action trace")
        workflow = RetrievalWorkflow(policy, identity["arm"], contracts=frozen_contracts)
        compliant, usage, retrieval_seconds, rejected = True, Counter(), 0.0, 0
        for action in row["trace"]:
            if action.get("status") == "rejected":
                if not isinstance(action.get("error"), str) or not action["error"]:
                    raise ValueError("Rejected actions require an explicit error")
                rejected += 1
                compliant = False
                continue
            if action["name"] in ("shell", "finish"):
                try:
                    workflow.guard(action["name"])
                except ValueError:
                    compliant = False
                continue
            event = action["event"]
            if event["transport"] == "offline_fixture":
                raise ValueError("Offline fixtures cannot be published as model retrieval evidence")
            replayed = workflow.retrieve(
                action["name"], event["arguments"], lambda *_, value=event["payload"]: value, event["transport"],
            )
            if (
                replayed["payload_sha256"] != event["payload_sha256"]
                or replayed["output_sha256"] != event["output_sha256"] or replayed["output"] != event["output"]
            ):
                raise ValueError("Retrieval payload or model-visible output changed")
            if (
                type(event.get("seconds")) not in (int, float)
                or event["seconds"] < 0 or not math.isfinite(event["seconds"])
            ):
                raise ValueError("Missing retrieval latency measurement")
            usage[replayed["evidence"]["status"]] += 1
            retrieval_seconds += event["seconds"]
        if policy == "required" and not PROVIDERS[identity["arm"]] <= workflow.attempted:
            compliant = False
        seen[row["id"]] = {
            **identity, "generation_status": row["status"], "passed": passed,
            "evaluation_status": evaluation_status, "rejected_actions": rejected,
            "retrieval_compliant": compliant, "retrieval_calls": workflow.calls,
            "retrieval_statuses": dict(usage), "retrieval_seconds": retrieval_seconds,
            **{field: row[field] for field in ("cost_micro_usd", "input_tokens", "output_tokens", "generation_seconds")},
        }
    complete = len(seen) == len(expected) and all(
        row["generation_status"] not in ("client_error", "not_started")
        and row["evaluation_status"] != "invalid_report" for row in seen.values()
    )
    tracks = {}
    for track in TRACKS:
        tracks[track] = {}
        for arm in ARMS:
            assigned = [row for row in expected.values() if row["track"] == track and row["arm"] == arm]
            actual = [seen[row["id"]] for row in assigned if row["id"] in seen]
            paired_baselines = [
                (row, seen.get(f"{row['task_id']}.baseline.r{row['repeat']}")) for row in actual
            ]
            tracks[track][arm] = {
                "assigned": len(assigned), "observed": len(actual),
                "missing": len(assigned) - len(actual),
                "resolved": sum(row["passed"] for row in actual),
                "resolved_fraction_all_assigned_lower_bound": sum(row["passed"] for row in actual) / len(assigned),
                "attempts_invoking_retrieval": sum(row["retrieval_calls"] > 0 for row in actual),
                "required_use_noncompliant": sum(not row["retrieval_compliant"] for row in actual),
                "rejected_actions": sum(row["rejected_actions"] for row in actual),
                "regressions_vs_baseline_observed": sum(
                    baseline is not None and baseline["passed"] and not row["passed"]
                    for row, baseline in paired_baselines
                ),
                "improvements_vs_baseline_observed": sum(
                    baseline is not None and not baseline["passed"] and row["passed"]
                    for row, baseline in paired_baselines
                ),
                "cost_micro_usd_observed": sum(row["cost_micro_usd"] for row in actual),
                "input_tokens_observed": sum(row["input_tokens"] for row in actual),
                "output_tokens_observed": sum(row["output_tokens"] for row in actual),
                "generation_seconds_observed": sum(row["generation_seconds"] for row in actual),
                "retrieval_seconds_observed": sum(row["retrieval_seconds"] for row in actual),
                "relevant_evidence_rate": None, "correct_application_rate": None,
                "evidence_review": "pending; calls and scores are not relevance judgments",
            }
    pairs = {}
    if complete:
        fractions = {
            arm: {
                task["id"]: statistics.mean(
                    row["passed"] for row in seen.values() if row["task_id"] == task["id"] and row["arm"] == arm
                ) for task in manifest["tasks"]
            } for arm in ARMS
        }
        pairs = {
            f"{left}_vs_{right}": clustered_pair(fractions[left], fractions[right], f"{SEED}:{policy}:{left}:{right}")
            for left, right in combinations(ARMS, 2)
        }
        holm(pairs)
    return {
        "status": "complete_unreviewed" if complete else "incomplete",
        "policy": policy, "assigned": len(expected), "observed": len(seen),
        "missing": sorted(set(expected) - seen.keys()),
        "tracks": tracks, "paired_task_cluster_comparisons": pairs, "attempts": list(seen.values()),
        "suite_sha256": sha((root / "manifest.json").read_bytes()),
        "observations_sha256": sha(observations.read_bytes()),
        "superiority_claim_supported": False,
        "retrieval_quality_evaluable": False,
        "required_policy_compliant": (
            complete and all(row["retrieval_compliant"] for row in seen.values()) if policy == "required" else None
        ),
        "limitations": [
            "Independent task/source/evidence review and model-client provenance verification remain pending.",
            "Incomplete outcomes use an explicitly labeled all-assigned lower bound; no paired inference until complete.",
            "Whole task clusters, not repeated attempts, are resampled; six overall tests use within-policy Holm correction.",
            "Noncompliance and failed/empty retrieval remain in denominators, not selectively rerun or excluded.",
            "This reporter checks supplied artifacts and hashes, not the identity of the external collector.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("freeze", "self-test", "grade", "replay", "report"))
    parser.add_argument("--frozen", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image")
    parser.add_argument("--model")
    parser.add_argument("--task")
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--policy", choices=("optional", "required"), default="optional")
    parser.add_argument("--arm", choices=ARMS, default="baseline")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--real-backendpro", action="store_true", help="Replay BackendPro through actual local MCP; Context7 stays fixture-only")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; never overwrite frozen evidence")
    try:
        if args.mode == "freeze":
            if not args.image:
                parser.error("freeze requires --image")
            result = freeze(args.output, args.image, args.model)
        elif args.mode == "replay":
            if not args.input:
                parser.error("replay requires --input containing fixture actions")
            result = replay(args.policy, args.arm, json.loads(args.input.read_bytes()), args.real_backendpro)
            write_new(args.output, result)
        else:
            if args.frozen is None:
                parser.error("This mode requires --frozen")
            if args.mode == "self-test":
                result = self_test(args.frozen, args.output)
            elif args.mode == "grade":
                if not args.task or not args.candidate:
                    parser.error("grade requires --task and --candidate")
                result = grade(args.frozen, args.task, args.candidate)
                write_new(args.output, result)
            else:
                if not args.input:
                    parser.error("report requires --input observations")
                result = report(args.frozen, args.input, args.policy)
                write_new(args.output, result)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    print(result["status"])
    if args.mode == "self-test" and result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
