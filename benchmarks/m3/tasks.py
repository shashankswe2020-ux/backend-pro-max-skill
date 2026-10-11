"""Author-created draft tasks. References/checks are never exported to agent workspaces."""
from textwrap import dedent


def task(identifier, track, problem, reference, mutation, checks, sources=()):
    reference = dedent(reference).strip() + "\n"
    old, new = mutation
    if reference.count(old) != 1:
        raise ValueError(f"Ambiguous starter mutation: {identifier}")
    return {
        "id": identifier, "track": track, "problem": problem,
        "starter": reference.replace(old, new, 1), "reference": reference,
        "checks": dedent(checks).strip() + "\n", "source_urls": list(sources),
        "review_status": "pending_independent_review",
    }


TASKS = [
    task("backend-01", "backend",
         "Fix transfer(accounts, src, dst, amount, fail=False). A positive integer amount must move atomically between distinct existing accounts. Reject invalid amounts, same-account transfers, or insufficient funds with ValueError. Missing accounts raise KeyError. fail=True injects RuntimeError after the debit. Every failure must leave the input dict unchanged.",
         """
         def transfer(accounts, src, dst, amount, fail=False):
             if type(amount) is not int or amount <= 0 or src == dst:
                 raise ValueError("invalid transfer")
             if accounts[src] < amount:
                 raise ValueError("insufficient funds")
             accounts[dst]
             staged = accounts.copy()
             staged[src] -= amount
             if fail:
                 raise RuntimeError("injected failure after debit")
             staged[dst] += amount
             accounts.update(staged)
         """, ("staged = accounts.copy()", "staged = accounts"),
         """
         accounts = {"a": 10, "b": 2}
         with self.assertRaises(RuntimeError):
             s.transfer(accounts, "a", "b", 3, fail=True)
         self.assertEqual(accounts, {"a": 10, "b": 2})
         for amount in (0, -1, 20, True):
             with self.assertRaises(ValueError):
                 s.transfer(accounts, "a", "b", amount)
             self.assertEqual(accounts, {"a": 10, "b": 2})
         with self.assertRaises(KeyError):
             s.transfer(accounts, "a", "missing", 3)
         with self.assertRaises(ValueError):
             s.transfer(accounts, "a", "a", 1)
         self.assertEqual(accounts, {"a": 10, "b": 2})
         s.transfer(accounts, "a", "b", 3)
         self.assertEqual(accounts, {"a": 7, "b": 5})
         """),
    task("backend-02", "backend",
         "Fix total_effect(events). Each event is (id, integer amount). Apply each id exactly once within this call, even for non-adjacent redelivery; the first occurrence wins. Empty input returns 0. Do not mutate the input.",
         """
         def total_effect(events):
             seen = set()
             total = 0
             for identifier, amount in events:
                 if identifier in seen:
                     continue
                 seen.add(identifier)
                 total += amount
             return total
         """, ("if identifier in seen:", "if False:"),
         """
         events = [("a", 5), ("b", 2), ("a", 99), ("c", -1), ("b", 2)]
         before = list(events)
         self.assertEqual(s.total_effect(events), 6)
         self.assertEqual(events, before)
         self.assertEqual(s.total_effect([]), 0)
         self.assertEqual(s.total_effect([("x", 0), ("x", 8)]), 0)
         """),
    task("backend-03", "backend",
         "Fix delays(attempts, base, cap), returning attempts exponential-backoff delays beginning at base and capped at cap. attempts must be a nonnegative integer (not bool); base and cap must be positive. Invalid arguments raise ValueError. Zero attempts returns [].",
         """
         def delays(attempts, base, cap):
             if type(attempts) is not int or attempts < 0 or base <= 0 or cap <= 0:
                 raise ValueError("invalid backoff")
             result = []
             delay = min(base, cap)
             for _ in range(attempts):
                 result.append(delay)
                 delay = min(delay * 2, cap)
             return result
         """, ("delay = min(delay * 2, cap)", "delay = delay * 2"),
         """
         self.assertEqual(s.delays(6, .5, 2), [.5, 1, 2, 2, 2, 2])
         self.assertEqual(s.delays(3, 8, 2), [2, 2, 2])
         self.assertEqual(s.delays(0, 1, 2), [])
         for args in ((-1, 1, 2), (True, 1, 2), (2, 0, 2), (2, 1, 0)):
             with self.assertRaises(ValueError):
                 s.delays(*args)
         """),
    task("backend-04", "backend",
         "Fix Cache(ttl).get(key, now, loader). ttl must be positive. A cached value is valid strictly before its insertion time plus ttl; refresh at the exact boundary. Cache successful loader results including None, but propagate loader failures and never cache failures. Time is supplied explicitly; no sleeping or background work.",
         """
         class Cache:
             def __init__(self, ttl):
                 if ttl <= 0:
                     raise ValueError("ttl")
                 self.ttl, self.values = ttl, {}
             def get(self, key, now, loader):
                 if key in self.values and now < self.values[key][0]:
                     return self.values[key][1]
                 value = loader()
                 self.values[key] = (now + self.ttl, value)
                 return value
         """, ("now < self.values[key][0]", "now <= self.values[key][0]"),
         """
         c = s.Cache(10)
         calls = []
         def load():
             calls.append(1)
             return len(calls)
         self.assertEqual(c.get("k", 0, load), 1)
         self.assertEqual(c.get("k", 9, load), 1)
         self.assertEqual(c.get("k", 10, load), 2)
         def fail():
             raise RuntimeError("loader failed")
         with self.assertRaises(RuntimeError):
             c.get("bad", 0, fail)
         self.assertEqual(c.get("bad", 1, load), 3)
         self.assertIsNone(c.get("none", 0, lambda: None))
         self.assertIsNone(c.get("none", 1, fail))
         with self.assertRaises(ValueError):
             s.Cache(0)
         """),
    task("backend-05", "backend",
         "Fix Inventory(stock).reserve() for concurrent callers. reserve returns True and consumes one item only when stock is positive, otherwise False. stock must remain nonnegative, and successes must equal consumed stock. Preserve the public stock attribute; reject negative initial stock with ValueError.",
         """
         import threading
         import time
         class Inventory:
             def __init__(self, stock):
                 if stock < 0:
                     raise ValueError("stock")
                 self.stock = stock
                 self.lock = threading.Lock()
             def reserve(self):
                 with self.lock:
                     if self.stock <= 0:
                         return False
                     current = self.stock
                     time.sleep(.002)
                     self.stock = current - 1
                     return True
         """, ("with self.lock:", "if True:"),
         """
         from concurrent.futures import ThreadPoolExecutor
         inventory = s.Inventory(10)
         with ThreadPoolExecutor(max_workers=20) as pool:
             successes = list(pool.map(lambda _: inventory.reserve(), range(60)))
         self.assertEqual(sum(successes), 10)
         self.assertEqual(inventory.stock, 0)
         self.assertFalse(inventory.reserve())
         with self.assertRaises(ValueError):
             s.Inventory(-1)
         """),
    task("backend-06", "backend",
         "Fix Limiter(limit, window).allow(key, now): a fixed window begins with each key's first allowed request. Allow limit requests per key per window; rejected requests do not slide the window. At now >= window start + window, reset that key's count. Both constructor values must be positive.",
         """
         class Limiter:
             def __init__(self, limit, window):
                 if limit <= 0 or window <= 0:
                     raise ValueError("limits")
                 self.limit, self.window, self.state = limit, window, {}
             def allow(self, key, now):
                 start, count = self.state.get(key, (now, 0))
                 if now >= start + self.window:
                     start, count = now, 0
                 if count >= self.limit:
                     return False
                 self.state[key] = (start, count + 1)
                 return True
         """, ("self.state.get(key, (now, 0))", "next(iter(self.state.values()), (now, 0))"),
         """
         limiter = s.Limiter(2, 10)
         self.assertTrue(limiter.allow("a", 0))
         self.assertTrue(limiter.allow("a", 1))
         self.assertFalse(limiter.allow("a", 9))
         self.assertTrue(limiter.allow("b", 9))
         self.assertTrue(limiter.allow("a", 10))
         self.assertTrue(limiter.allow("a", 11))
         self.assertFalse(limiter.allow("a", 12))
         with self.assertRaises(ValueError):
             s.Limiter(0, 10)
         """),
    task("framework-01", "framework",
         "For Pydantic 2.14.0, fix Payload so qty accepts only integer inputs without coercion, and unknown fields are forbidden. Preserve model_validate and model_dump behavior for valid qty=2. Validation failures must be Pydantic ValidationError.",
         """
         from pydantic import BaseModel, ConfigDict
         class Payload(BaseModel):
             model_config = ConfigDict(strict=True, extra="forbid")
             qty: int
         """, ('ConfigDict(strict=True, extra="forbid")', 'ConfigDict()'),
         """
         from pydantic import ValidationError
         self.assertEqual(s.Payload.model_validate({"qty": 2}).model_dump(), {"qty": 2})
         for data in ({"qty": "2"}, {"qty": True}, {"qty": 2, "extra": 1}):
             with self.assertRaises(ValidationError):
                 s.Payload.model_validate(data)
         """, ("https://docs.pydantic.dev/latest/api/config/",)),
    task("framework-02", "framework",
         "For Pydantic 2.14.0, fix User so userId is the external alias of user_id. Accept either spelling on input. model_dump(by_alias=True) must emit userId; ordinary model_dump must emit user_id.",
         """
         from pydantic import BaseModel, ConfigDict, Field
         class User(BaseModel):
             model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)
             user_id: int = Field(alias="userId")
         """, ("validate_by_name=True", "validate_by_name=False"),
         """
         for data in ({"userId": 7}, {"user_id": 7}):
             user = s.User.model_validate(data)
             self.assertEqual(user.model_dump(), {"user_id": 7})
             self.assertEqual(user.model_dump(by_alias=True), {"userId": 7})
         """, ("https://docs.pydantic.dev/latest/concepts/alias/",)),
    task("framework-03", "framework",
         "For Pydantic 2.14.0, fix Named so name is stripped and lowercased before storage. Reject empty/whitespace-only names and non-string inputs with ValidationError; do not stringify numbers or None.",
         """
         from pydantic import BaseModel, field_validator
         class Named(BaseModel):
             name: str
             @field_validator("name", mode="before")
             @classmethod
             def normalize(cls, value):
                 if not isinstance(value, str) or not value.strip():
                     raise ValueError("name")
                 return value.strip().lower()
         """, ("return value.strip().lower()", "return value"),
         """
         from pydantic import ValidationError
         self.assertEqual(s.Named(name="  ALICE  ").name, "alice")
         for value in ("", "  ", 1, None):
             with self.assertRaises(ValidationError):
                 s.Named(name=value)
         """, ("https://docs.pydantic.dev/latest/concepts/validators/",)),
    task("framework-04", "framework",
         "For Starlette 1.7.0, expose app with GET /items/{item_id} accepting nonnegative integer path IDs. Return JSON {\"id\": integer}; non-integer paths must be 404 rather than a handler exception or a string-valued ID.",
         """
         from starlette.applications import Starlette
         from starlette.responses import JSONResponse
         from starlette.routing import Route
         async def item(request):
             return JSONResponse({"id": request.path_params["item_id"]})
         app = Starlette(routes=[Route("/items/{item_id:int}", item)])
         """, ('"/items/{item_id:int}"', '"/items/{item_id}"'),
         """
         from starlette.testclient import TestClient
         with TestClient(s.app) as client:
             response = client.get("/items/12")
             self.assertEqual(response.status_code, 200)
             self.assertEqual(response.json(), {"id": 12})
             self.assertEqual(client.get("/items/not-int").status_code, 404)
             self.assertEqual(client.get("/items/0").json(), {"id": 0})
         """, ("https://www.starlette.io/routing/",)),
    task("framework-05", "framework",
         "For Starlette 1.7.0, fix app lifespan handling. app.state.ready starts False, is True inside a TestClient context, and returns False after shutdown. app.state.closed starts False and becomes True after shutdown. Use the supported lifespan API.",
         """
         from contextlib import asynccontextmanager
         from starlette.applications import Starlette
         @asynccontextmanager
         async def lifespan(app):
             app.state.ready = True
             try:
                 yield
             finally:
                 app.state.ready = False
                 app.state.closed = True
         app = Starlette(lifespan=lifespan)
         app.state.ready = False
         app.state.closed = False
         """, ("Starlette(lifespan=lifespan)", "Starlette()"),
         """
         from starlette.testclient import TestClient
         self.assertFalse(s.app.state.ready)
         self.assertFalse(s.app.state.closed)
         with TestClient(s.app):
             self.assertTrue(s.app.state.ready)
             self.assertFalse(s.app.state.closed)
         self.assertFalse(s.app.state.ready)
         self.assertTrue(s.app.state.closed)
         """, ("https://www.starlette.io/lifespan/",)),
    task("framework-06", "framework",
         "For HTTPX 0.28.1, fix fetch(transport, url) to use the supplied transport, a 2-second timeout for all phases, raise HTTPStatusError for unsuccessful HTTP status, and return parsed JSON on success. Preserve JSON parsing failures. Do not access the real network.",
         """
         import httpx
         def fetch(transport, url):
             with httpx.Client(transport=transport, timeout=2.0) as client:
                 response = client.get(url)
                 response.raise_for_status()
                 return response.json()
         """, ("response.raise_for_status()", "pass"),
         """
         import httpx
         def handler(request):
             self.assertTrue(all(v == 2.0 for v in request.extensions["timeout"].values()))
             return httpx.Response(200, json={"ok": True})
         self.assertEqual(s.fetch(httpx.MockTransport(handler), "https://example.test"), {"ok": True})
         with self.assertRaises(httpx.HTTPStatusError):
             s.fetch(httpx.MockTransport(lambda r: httpx.Response(404, json={})), "https://example.test")
         with self.assertRaises(ValueError):
             s.fetch(httpx.MockTransport(lambda r: httpx.Response(200, text="not json")), "https://example.test")
         """, ("https://www.python-httpx.org/advanced/transports/",)),
    task("mixed-01", "mixed",
         "Fix this Starlette 1.7.0 payment endpoint. POST /pay requires Idempotency-Key and JSON with a positive integer amount. Bad input returns 400. The first valid request returns {\"charge\": n}, starting at 1. Replaying the same key/amount returns that same response without another charge; changing amount for that key returns 409. Sequential in-process behavior is sufficient; do not claim durable/distributed idempotency.",
         """
         from starlette.applications import Starlette
         from starlette.responses import JSONResponse
         from starlette.routing import Route
         async def pay(request):
             key = request.headers.get("Idempotency-Key")
             try:
                 body = await request.json()
             except ValueError:
                 return JSONResponse({}, status_code=400)
             amount = body.get("amount") if isinstance(body, dict) else None
             if not key or type(amount) is not int or amount <= 0:
                 return JSONResponse({}, status_code=400)
             if key in request.app.state.results:
                 old_amount, response = request.app.state.results[key]
                 return JSONResponse(response if amount == old_amount else {}, status_code=200 if amount == old_amount else 409)
             request.app.state.charges += 1
             response = {"charge": request.app.state.charges}
             request.app.state.results[key] = (amount, response)
             return JSONResponse(response)
         app = Starlette(routes=[Route("/pay", pay, methods=["POST"])])
         app.state.results, app.state.charges = {}, 0
         """, ("if key in request.app.state.results:", "if False:"),
         """
         from starlette.testclient import TestClient
         with TestClient(s.app) as client:
             self.assertEqual(client.post("/pay", json={"amount": 2}).status_code, 400)
             for amount in (0, -1, True, "2"):
                 self.assertEqual(client.post("/pay", headers={"Idempotency-Key": "bad"}, json={"amount": amount}).status_code, 400)
             first = client.post("/pay", headers={"Idempotency-Key": "a"}, json={"amount": 2})
             again = client.post("/pay", headers={"Idempotency-Key": "a"}, json={"amount": 2})
             self.assertEqual(first.json(), {"charge": 1})
             self.assertEqual(again.json(), first.json())
             self.assertEqual(client.post("/pay", headers={"Idempotency-Key": "a"}, json={"amount": 3}).status_code, 409)
             self.assertEqual(s.app.state.charges, 1)
         """, ("https://www.starlette.io/requests/",)),
    task("mixed-02", "mixed",
         "For Pydantic 2.14.0, model Money with a positive Decimal amount of at most two decimal places and currency restricted to USD or EUR. Preserve decimal precision; JSON-mode dumps must encode amount as a string. Reject zero, negative values, excess precision, and other currencies.",
         """
         from decimal import Decimal
         from typing import Literal
         from pydantic import BaseModel, Field
         class Money(BaseModel):
             amount: Decimal = Field(gt=0, decimal_places=2)
             currency: Literal["USD", "EUR"]
         """, ("decimal_places=2", "decimal_places=4"),
         """
         from decimal import Decimal
         from pydantic import ValidationError
         money = s.Money(amount="0.10", currency="USD")
         self.assertIsInstance(money.amount, Decimal)
         self.assertEqual(money.amount, Decimal("0.10"))
         self.assertIsInstance(money.model_dump(mode="json")["amount"], str)
         for data in ({"amount": "1.001", "currency": "USD"}, {"amount": "0", "currency": "EUR"}, {"amount": "-1", "currency": "USD"}, {"amount": "1", "currency": "XXX"}):
             with self.assertRaises(ValidationError):
                 s.Money(**data)
         """, ("https://docs.pydantic.dev/latest/api/standard_library_types/",)),
    task("mixed-03", "mixed",
         "For Pydantic 2.14.0, fix Window(start, end) to accept only timezone-aware datetimes with end strictly after start. Compare instants across different UTC offsets. Invalid windows must raise ValidationError.",
         """
         from datetime import datetime
         from pydantic import BaseModel, model_validator
         class Window(BaseModel):
             start: datetime
             end: datetime
             @model_validator(mode="after")
             def valid(self):
                 if self.start.utcoffset() is None or self.end.utcoffset() is None or self.end <= self.start:
                     raise ValueError("invalid window")
                 return self
         """, ("or self.end <= self.start", "or False"),
         """
         from pydantic import ValidationError
         valid = s.Window(start="2026-01-01T10:00:00+02:00", end="2026-01-01T09:00:00Z")
         self.assertGreater(valid.end, valid.start)
         for start, end in (("2026-01-01T10:00:00Z", "2026-01-01T09:00:00Z"), ("2026-01-01T10:00:00Z", "2026-01-01T10:00:00Z"), ("2026-01-01T10:00:00", "2026-01-01T11:00:00Z")):
             with self.assertRaises(ValidationError):
                 s.Window(start=start, end=end)
         """, ("https://docs.pydantic.dev/latest/concepts/validators/",)),
    task("mixed-04", "mixed",
         "For Starlette 1.7.0, fix make_app(origins) for credentialed CORS. Only supplied explicit origins may pass preflight; reject a wildcard configuration with ValueError. GET / returns {\"ok\": true}. Allow GET preflight from approved origins and reject other origins.",
         """
         from starlette.applications import Starlette
         from starlette.middleware import Middleware
         from starlette.middleware.cors import CORSMiddleware
         from starlette.responses import JSONResponse
         from starlette.routing import Route
         async def home(request):
             return JSONResponse({"ok": True})
         def make_app(origins):
             if "*" in origins:
                 raise ValueError("explicit origins required")
             return Starlette(routes=[Route("/", home)], middleware=[Middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET"])])
         """, ("allow_origins=origins", 'allow_origins=["*"]'),
         """
         from starlette.testclient import TestClient
         with self.assertRaises(ValueError):
             s.make_app(["*"])
         with TestClient(s.make_app(["https://approved.test"])) as client:
             self.assertEqual(client.get("/").json(), {"ok": True})
             for origin, status in (("https://approved.test", 200), ("https://other.test", 400)):
                 response = client.options("/", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
                 self.assertEqual(response.status_code, status)
                 if status == 200:
                     self.assertEqual(response.headers["access-control-allow-origin"], origin)
                     self.assertEqual(response.headers["access-control-allow-credentials"], "true")
         """, ("https://www.starlette.io/middleware/",)),
    task("mixed-05", "mixed",
         "For Starlette 1.7.0, handle only Overloaded with HTTP 503, JSON {\"retryable\": true}, and Retry-After: 5. /busy raises Overloaded. /bug raises ValueError and must remain an unhandled programming error, not be disguised as overload. Expose app.",
         """
         from starlette.applications import Starlette
         from starlette.responses import JSONResponse
         from starlette.routing import Route
         class Overloaded(Exception):
             pass
         async def busy(request):
             raise Overloaded("busy")
         async def bug(request):
             raise ValueError("bug")
         async def overload(request, exc):
             return JSONResponse({"retryable": True}, status_code=503, headers={"Retry-After": "5"})
         app = Starlette(routes=[Route("/busy", busy), Route("/bug", bug)], exception_handlers={Overloaded: overload})
         """, ("{Overloaded: overload}", "{Exception: overload}"),
         """
         from starlette.testclient import TestClient
         with TestClient(s.app) as client:
             response = client.get("/busy")
             self.assertEqual(response.status_code, 503)
             self.assertEqual(response.json(), {"retryable": True})
             self.assertEqual(response.headers["retry-after"], "5")
             with self.assertRaises(ValueError):
                 client.get("/bug")
         """, ("https://www.starlette.io/exceptions/",)),
    task("mixed-06", "mixed",
         "For Starlette 1.7.0, fix make_app(storage): POST /save requires Idempotency-Key, calls synchronous storage.write(key) once per successful key, and returns {\"saved\": true}. Missing keys return 400. TimeoutError returns 503 and must not mark the key complete; retries must call storage again. Replays after success must not call storage. This task is sequential/in-process only.",
         """
         from starlette.applications import Starlette
         from starlette.responses import JSONResponse
         from starlette.routing import Route
         def make_app(storage):
             completed = set()
             async def save(request):
                 key = request.headers.get("Idempotency-Key")
                 if not key:
                     return JSONResponse({}, status_code=400)
                 if key not in completed:
                     try:
                         storage.write(key)
                     except TimeoutError:
                         return JSONResponse({}, status_code=503)
                     completed.add(key)
                 return JSONResponse({"saved": True})
             return Starlette(routes=[Route("/save", save, methods=["POST"])])
         """, ("except TimeoutError:\n                return", "except TimeoutError:\n                completed.add(key)\n                return"),
         """
         from starlette.testclient import TestClient
         class Storage:
             calls = 0
             def write(self, key):
                 self.calls += 1
                 if self.calls == 1:
                     raise TimeoutError("injected")
         storage = Storage()
         with TestClient(s.make_app(storage)) as client:
             self.assertEqual(client.post("/save").status_code, 400)
             self.assertEqual(client.post("/save", headers={"Idempotency-Key": "a"}).status_code, 503)
             self.assertEqual(client.post("/save", headers={"Idempotency-Key": "a"}).json(), {"saved": True})
             self.assertEqual(client.post("/save", headers={"Idempotency-Key": "a"}).json(), {"saved": True})
             self.assertEqual(storage.calls, 2)
         """, ("https://www.starlette.io/requests/",)),
    task("control-01", "control", "Change LABEL from 'Retyr policy' to exactly 'Retry policy'. Preserve delay(n) = 2*n.",
         'LABEL = "Retry policy"\ndef delay(n):\n    return 2 * n\n',
         ("Retry policy", "Retyr policy"),
         'self.assertEqual(s.LABEL, "Retry policy")\nself.assertEqual([s.delay(n) for n in (0, 1, 5)], [0, 2, 10])'),
    task("control-02", "control", "Replace TUTORIAL_URL with exactly https://example.test/new-guide. Preserve TIMEOUT=30.",
         'TUTORIAL_URL = "https://example.test/new-guide"\nTIMEOUT = 30\n',
         ("new-guide", "old-guide"),
         'self.assertEqual(s.TUTORIAL_URL, "https://example.test/new-guide")\nself.assertEqual(s.TIMEOUT, 30)'),
    task("control-03", "control", "Change status_label() to return exactly 'Ready' rather than 'READY'. Preserve identity(value) for all objects.",
         'def status_label():\n    return "Ready"\ndef identity(value):\n    return value\n',
         ('"Ready"', '"READY"'),
         'self.assertEqual(s.status_label(), "Ready")\nobj = object()\nself.assertIs(s.identity(obj), obj)'),
    task("control-04", "control", "Fix the module docstring typo 'transactoin' to 'transaction'. Preserve add(a,b).",
         '"""A transaction example."""\ndef add(a, b):\n    return a + b\n',
         ("transaction", "transactoin"),
         'self.assertEqual(s.__doc__, "A transaction example.")\nself.assertEqual(s.add(-2, 7), 5)'),
    task("control-05", "control", "Change EXAMPLE_TENANT to 'demo' as requested by the documentation maintainer. Preserve tenant_key(name) returning 'tenant:' plus name.",
         'EXAMPLE_TENANT = "demo"\ndef tenant_key(name):\n    return "tenant:" + name\n',
         ('"demo"', '"example-old"'),
         'self.assertEqual(s.EXAMPLE_TENANT, "demo")\nself.assertEqual(s.tenant_key("abc"), "tenant:abc")'),
    task("control-06", "control", "Remove the duplicate 'ping' from __all__, leaving exactly ['ping']. Preserve ping() returning 'pong'.",
         '__all__ = ["ping"]\ndef ping():\n    return "pong"\n',
         ('["ping"]', '["ping", "ping"]'),
         'self.assertEqual(s.__all__, ["ping"])\nself.assertEqual(s.ping(), "pong")'),
]
