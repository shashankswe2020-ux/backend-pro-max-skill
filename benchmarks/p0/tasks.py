"""Public development cases, not independently reviewed or held-out evidence."""
from textwrap import dedent

AUTHOR = "backendpro-p0-development"
TASKS = []


def family(name, track, problem, files, checks, cases, sources=()):
    reference = {path: dedent(source).strip() + "\n" for path, source in files.items()}
    for number, (scenario, edits) in enumerate(cases, 1):
        starter = dict(reference)
        for path, old, new in edits:
            if starter[path].count(old) != 1:
                raise ValueError(f"Ambiguous mutation: {name}/{scenario}/{path}: {old}")
            starter[path] = starter[path].replace(old, new, 1)
        TASKS.append({
            "id": f"{name}-{number:02}", "track": track, "repository": name,
            "family": name, "split": "development", "author": AUTHOR,
            "problem": problem + "\nReported regression: " + scenario,
            "starter": starter, "reference": reference,
            "checks": dedent(checks).strip() + "\n",
            "source_urls": list(sources), "license": "MIT",
            "review_status": "pending_independent_review",
        })


family(
    "ledger", "backend",
    """Repair the SQLite ledger across app.py and store.py. Store() owns an in-memory
database. open_account(name, balance) initializes an account. transfer(store, key,
src, dst, amount, fail=False) returns the destination's resulting balance.
Amounts must be positive exact ints, not bool; accounts must exist and differ,
and funds must suffice. Invalid transfers raise ValueError (missing account:
KeyError) without writes. Each key stores the original request and result:
identical replay returns the stored result even after later transfers; reuse
with different arguments raises ValueError. fail=True raises RuntimeError after
the debit and must roll back both balances and the key, allowing retry. Successful
debit, credit, and receipt commit together. Preserve all public entry points.""",
    {
        "store.py": """
            import sqlite3
            class Store:
                def __init__(self):
                    self.db = sqlite3.connect(":memory:")
                    self.db.executescript("CREATE TABLE accounts(name TEXT PRIMARY KEY, balance INTEGER);"
                        "CREATE TABLE receipts(key TEXT PRIMARY KEY, src TEXT, dst TEXT, amount INTEGER, result INTEGER);")
                def open_account(self, name, balance):
                    with self.db:
                        self.db.execute("INSERT INTO accounts VALUES(?,?)", (name, balance))
                def balance(self, name):
                    row = self.db.execute("SELECT balance FROM accounts WHERE name=?", (name,)).fetchone()
                    if row is None:
                        raise KeyError(name)
                    return row[0]
                def receipt(self, key):
                    return self.db.execute("SELECT src,dst,amount,result FROM receipts WHERE key=?", (key,)).fetchone()
                def move(self, key, src, dst, amount, fail):
                    with self.db:
                        self.db.execute("UPDATE accounts SET balance=balance-? WHERE name=?", (amount, src))
                        if fail:
                            raise RuntimeError("after debit")
                        self.db.execute("UPDATE accounts SET balance=balance+? WHERE name=?", (amount, dst))
                        result = self.balance(dst)
                        self.db.execute("INSERT INTO receipts VALUES(?,?,?,?,?)", (key, src, dst, amount, result))
                    return result
        """,
        "app.py": """
            from store import Store
            def transfer(store, key, src, dst, amount, fail=False):
                if type(amount) is not int or amount <= 0 or src == dst:
                    raise ValueError("invalid transfer")
                previous = store.receipt(key)
                if previous is not None:
                    if tuple(previous[:3]) != (src, dst, amount):
                        raise ValueError("key conflict")
                    return previous[3]
                if store.balance(src) < amount:
                    raise ValueError("insufficient funds")
                store.balance(dst)
                return store.move(key, src, dst, amount, fail)
        """,
    },
    """
        db = s.Store()
        db.open_account("a", 100)
        db.open_account("b", 0)
        for args, error in [(("a","b",True), ValueError), (("a","a",2), ValueError),
                            (("a","b",101), ValueError), (("a","missing",2), KeyError)]:
            with self.assertRaises(error):
                s.transfer(db, "invalid", *args)
            self.assertEqual((db.balance("a"), db.balance("b")), (100,0))
        with self.assertRaises(RuntimeError):
            s.transfer(db, "retry", "a", "b", 10, fail=True)
        self.assertEqual((db.balance("a"), db.balance("b")), (100,0))
        self.assertIsNone(db.receipt("retry"))
        self.assertEqual(s.transfer(db, "retry", "a", "b", 10), 10)
        self.assertEqual(s.transfer(db, "later", "a", "b", 5), 15)
        self.assertEqual(s.transfer(db, "retry", "a", "b", 10), 10)
        with self.assertRaises(ValueError):
            s.transfer(db, "retry", "a", "b", 11)
        self.assertEqual((db.balance("a"), db.balance("b")), (85,15))
        self.assertEqual(db.receipt("retry"), ("a","b",10,10))
    """,
    [
        ("rollback and amount validation", [
            ("store.py", 'if fail:\n                raise RuntimeError', 'if fail:\n                self.db.commit()\n                raise RuntimeError'),
            ("app.py", "type(amount) is not int", "not isinstance(amount, int)")]),
        ("debit/credit direction and replay result", [
            ("store.py", "balance=balance+?", "balance=balance-?"),
            ("app.py", "return previous[3]", "return store.balance(dst)")]),
        ("receipt content and conflicting replays", [
            ("store.py", "(key, src, dst, amount, result)", "(key, dst, src, amount, result)"),
            ("app.py", "if tuple(previous[:3]) != (src, dst, amount):", "if False:")]),
        ("balance lookup and funds boundary", [
            ("store.py", "return row[0]", "return 0"),
            ("app.py", "if store.balance(src) < amount:", "if False:")]),
        ("receipt lookup and same-account rejection", [
            ("store.py", "return self.db.execute(\"SELECT src,dst,amount,result FROM receipts WHERE key=?\", (key,)).fetchone()", "return None"),
            ("app.py", " or src == dst", "")]),
    ],
    ["https://docs.python.org/3.12/library/sqlite3.html#how-to-use-the-connection-context-manager"],
)

family(
    "leases", "backend",
    """Repair Queue and Worker across queue_store.py and app.py. Queue.put(key,
payload) is first-write-wins, including after acknowledgement. claim(now, ttl)
requires positive ttl and returns (key,payload,token) for the first available job,
or None. A lease becomes available at the exact expiry boundary. Each re-claim
gets a strictly newer token. ack(key,token,now) succeeds only for the current,
unexpired lease and permanently completes the job; stale/unknown ack returns
False. Claims and acks must be atomic across threads. Worker.run(now, ttl, handler)
processes at most one job; propagate handler errors without ack, and return the
ack result on success, using the same supplied logical time. No wall-clock sleeps
are needed for correctness. Preserve first insertion order.""",
    {
        "queue_store.py": """
            import threading
            class Queue:
                def __init__(self):
                    self.jobs = {}
                    self.lock = threading.Lock()
                    self.sequence = 0
                def put(self, key, payload):
                    with self.lock:
                        self.jobs.setdefault(key, [payload, 0, float("-inf"), False])
                def claim(self, now, ttl):
                    if ttl <= 0:
                        raise ValueError("ttl")
                    with self.lock:
                        for key, row in self.jobs.items():
                            if not row[3] and row[2] <= now:
                                self.sequence += 1
                                row[1], row[2] = self.sequence, now + ttl
                                return key, row[0], row[1]
                    return None
                def ack(self, key, token, now):
                    with self.lock:
                        row = self.jobs.get(key)
                        if row is None or row[3] or row[1] != token or now >= row[2]:
                            return False
                        row[3] = True
                        return True
        """,
        "app.py": """
            from queue_store import Queue
            class Worker:
                def __init__(self, queue):
                    self.queue = queue
                def run(self, now, ttl, handler):
                    job = self.queue.claim(now, ttl)
                    if job is None:
                        return False
                    key, payload, token = job
                    handler(payload)
                    return self.queue.ack(key, token, now)
        """,
    },
    """
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        q = s.Queue()
        q.put("a", 1)
        q.put("a", 999)
        first = q.claim(0, 10)
        self.assertEqual(first[:2], ("a",1))
        self.assertIsNone(q.claim(9,10))
        second = q.claim(10,10)
        self.assertGreater(second[2], first[2])
        self.assertFalse(q.ack("a", first[2], 11))
        self.assertFalse(q.ack("missing", 1, 11))
        self.assertFalse(q.ack("a", second[2], 20))
        third = q.claim(20,10)
        self.assertTrue(q.ack("a", third[2], 21))
        q.put("a", 2)
        self.assertIsNone(q.claim(100,10))
        with self.assertRaises(ValueError):
            q.claim(0,0)
        q = s.Queue()
        q.put("b", 7)
        def fail(value):
            raise RuntimeError("handler")
        worker = s.Worker(q)
        with self.assertRaises(RuntimeError):
            worker.run(0,5,fail)
        self.assertIsNone(q.claim(4,5))
        seen = []
        self.assertTrue(worker.run(5,5,seen.append))
        self.assertEqual(seen,[7])
        self.assertFalse(worker.run(6,5,seen.append))
        q = s.Queue()
        q.put("only", 42)
        barrier = Barrier(8)
        def claim(_):
            barrier.wait(timeout=3)
            return q.claim(0,10)
        with ThreadPoolExecutor(max_workers=8) as pool:
            claims = list(pool.map(claim, range(8)))
        self.assertEqual(sum(item is not None for item in claims), 1)
    """,
    [
        ("expiry boundary and failure acknowledgement", [
            ("queue_store.py", "row[2] <= now", "row[2] < now"),
            ("app.py", "handler(payload)", "self.queue.ack(key, token, now)\n        handler(payload)")]),
        ("stale tokens and handler payload", [
            ("queue_store.py", " or row[1] != token", ""),
            ("app.py", "handler(payload)", "handler(key)")]),
        ("expired acknowledgements and success result", [
            ("queue_store.py", " or now >= row[2]", ""),
            ("app.py", "return self.queue.ack(key, token, now)", "self.queue.ack(key, token, now)\n        return False")]),
        ("duplicate overwrite and missing-job return", [
            ("queue_store.py", "self.jobs.setdefault(key, [payload, 0, float(\"-inf\"), False])", "self.jobs[key] = [payload, 0, float('-inf'), False]"),
            ("app.py", "if job is None:\n            return False", "if job is None:\n            return True")]),
        ("token renewal and lease duration", [
            ("queue_store.py", "self.sequence += 1", "self.sequence = 1"),
            ("app.py", "self.queue.claim(now, ttl)", "self.queue.claim(now, ttl * 2)")]),
    ],
    ["https://docs.python.org/3.12/library/threading.html#lock-objects"],
)

family(
    "orders", "framework",
    """Repair parse_order and serialize_order with Pydantic 2.14.0. External JSON
uses orderId, items, currency; unknown fields are forbidden. orderId is a nonempty
string; items is a nonempty list of {sku,quantity,unit_cents}; sku is nonempty,
quantity is a strict positive integer, unit_cents is a strict nonnegative integer
(booleans and numeric strings rejected). Currency defaults to USD and only USD/EUR
are accepted. Duplicate skus are rejected. Validation raises pydantic.ValidationError.
serialize_order returns a plain JSON-compatible dict using orderId (not order_id)
and includes total_cents, computed as sum(quantity*unit_cents). Preserve caller
input and the Order and Item classes; validation and serialization use Pydantic v2.""",
    {
        "models.py": """
            from typing import Literal
            from pydantic import BaseModel, ConfigDict, Field, model_validator
            class Item(BaseModel):
                model_config = ConfigDict(extra="forbid")
                sku: str = Field(min_length=1)
                quantity: int = Field(strict=True, gt=0)
                unit_cents: int = Field(strict=True, ge=0)
            class Order(BaseModel):
                model_config = ConfigDict(extra="forbid")
                order_id: str = Field(alias="orderId", min_length=1)
                items: list[Item] = Field(min_length=1)
                currency: Literal["USD", "EUR"] = "USD"
                @model_validator(mode="after")
                def unique_skus(self):
                    if len({item.sku for item in self.items}) != len(self.items):
                        raise ValueError("duplicate sku")
                    return self
        """,
        "app.py": """
            from models import Item, Order
            def parse_order(data):
                return Order.model_validate(data)
            def serialize_order(order):
                result = order.model_dump(mode="json", by_alias=True)
                result["total_cents"] = sum(item.quantity * item.unit_cents for item in order.items)
                return result
        """,
    },
    """
        from copy import deepcopy
        from pydantic import ValidationError
        data = {"orderId":"o1","items":[{"sku":"a","quantity":2,"unit_cents":125},
                                      {"sku":"b","quantity":1,"unit_cents":0}]}
        before = deepcopy(data)
        parsed = s.parse_order(data)
        self.assertIsInstance(parsed, s.Order)
        self.assertIsInstance(parsed.items[0], s.Item)
        self.assertEqual(s.serialize_order(parsed), dict(data, currency="USD", total_cents=250))
        self.assertEqual(data, before)
        for key, value in [("quantity",True),("quantity","2"),("quantity",0),
                           ("unit_cents",False),("unit_cents",-1),("sku","")]:
            bad = deepcopy(data)
            bad["items"][0][key] = value
            with self.assertRaises(ValidationError):
                s.parse_order(bad)
        for extra in [{"extra":1},{"currency":"GBP"},{"items":[]},{"orderId":""},
                      {"items":[data["items"][0],data["items"][0]]}]:
            with self.assertRaises(ValidationError):
                s.parse_order(dict(data, **extra))
        bad = deepcopy(data)
        bad["items"][0]["unknown"] = 1
        with self.assertRaises(ValidationError):
            s.parse_order(bad)
        self.assertEqual(s.serialize_order(s.parse_order(dict(data,currency="EUR")))["currency"],"EUR")
    """,
    [
        ("strict quantities and external aliases", [
            ("models.py", "quantity: int = Field(strict=True, gt=0)", "quantity: int = Field(gt=0)"),
            ("app.py", "by_alias=True", "by_alias=False")]),
        ("duplicate items and quantity totals", [
            ("models.py", "if len({item.sku for item in self.items}) != len(self.items):", "if False:"),
            ("app.py", "item.quantity * item.unit_cents", "item.unit_cents")]),
        ("unknown order fields and total aggregation", [
            ("models.py", 'class Order(BaseModel):\n    model_config = ConfigDict(extra="forbid")', 'class Order(BaseModel):\n    model_config = ConfigDict(extra="ignore")'),
            ("app.py", "sum(item.quantity * item.unit_cents for item in order.items)", "0")]),
        ("empty item lists and caller mutation", [
            ("models.py", "items: list[Item] = Field(min_length=1)", "items: list[Item]"),
            ("app.py", "return Order.model_validate(data)", 'data.pop("currency", None)\n    return Order.model_validate(data)')]),
        ("strict prices and currency serialization", [
            ("models.py", "unit_cents: int = Field(strict=True, ge=0)", "unit_cents: int = Field(ge=0)"),
            ("app.py", 'result["total_cents"] =', 'result["currency"] = "USD"\n    result["total_cents"] =')]),
    ],
    ["https://docs.pydantic.dev/2.14/concepts/strict_mode/",
     "https://docs.pydantic.dev/2.14/concepts/serialization/"],
)

family(
    "pages", "framework",
    """Repair fetch_all(client, url, params=None, max_pages=10) using HTTPX 0.28.1.
The supplied sync Client remains caller-owned and open. Each response is JSON
{items: list, next: relative-or-absolute-URL-or-null}. Return items in page order.
Raise HTTPStatusError on HTTP errors, ValueError on invalid shape, cross-origin
next URL, repeated URL, or a next page beyond max_pages. max_pages is a positive
exact int. Resolve relative links against response.url. Apply params only on the
first request, do not mutate them, and never forward a request to another origin.
Origin comparison includes scheme, hostname and effective port. Do not follow
HTTP redirects; raise on them. Preserve helpers in navigation.py.""",
    {
        "navigation.py": """
            import httpx
            def next_url(current, link):
                target = httpx.URL(current).join(link)
                origin = httpx.URL(current)
                if (target.scheme, target.host, target.port) != (origin.scheme, origin.host, origin.port):
                    raise ValueError("cross origin")
                return str(target)
            def unpack(data):
                if not isinstance(data, dict) or not isinstance(data.get("items"), list):
                    raise ValueError("invalid page")
                link = data.get("next")
                if link is not None and (not isinstance(link, str) or not link):
                    raise ValueError("invalid next")
                return data["items"], link
        """,
        "app.py": """
            import httpx
            from navigation import next_url, unpack
            def fetch_all(client, url, params=None, max_pages=10):
                if type(max_pages) is not int or max_pages <= 0:
                    raise ValueError("max_pages")
                values, seen = [], set()
                for index in range(max_pages):
                    request = client.build_request("GET", url, params=params if index == 0 else None)
                    identity = str(request.url)
                    if identity in seen:
                        raise ValueError("cycle")
                    seen.add(identity)
                    response = client.send(request, follow_redirects=False)
                    response.raise_for_status()
                    items, link = unpack(response.json())
                    values.extend(items)
                    if link is None:
                        return values
                    url = next_url(str(response.url), link)
                raise ValueError("page limit")
        """,
    },
    """
        import httpx
        calls = []
        def handler(request):
            calls.append(str(request.url))
            if request.url.path == "/v1/start":
                return httpx.Response(200,json={"items":[1,2],"next":"page?cursor=2"})
            return httpx.Response(200,json={"items":[3],"next":None})
        params = {"filter":"x"}
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            self.assertEqual(s.fetch_all(client,"https://example.org/v1/start",params),[1,2,3])
            self.assertFalse(client.is_closed)
        self.assertEqual(calls,["https://example.org/v1/start?filter=x","https://example.org/v1/page?cursor=2"])
        self.assertEqual(params,{"filter":"x"})
        for link in ["https://evil.org/x","http://example.org/x","https://example.org:444/x","//evil.org/x"]:
            requests = []
            def foreign(request):
                requests.append(request)
                return httpx.Response(200,json={"items":[],"next":link})
            with httpx.Client(transport=httpx.MockTransport(foreign)) as client:
                with self.assertRaises(ValueError):
                    s.fetch_all(client,"https://example.org/start")
            self.assertEqual(len(requests),1)
        for status, data, error in [(503,{},httpx.HTTPStatusError),(302,{},httpx.HTTPStatusError),
                                    (200,{"items":"bad"},ValueError),
                                    (200,{"items":[],"next":3},ValueError)]:
            with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status,json=data))) as client:
                with self.assertRaises(error):
                    s.fetch_all(client,"https://example.org/start")
        count = []
        def cycle(request):
            count.append(1)
            return httpx.Response(200,json={"items":[1],"next":"/start"})
        with httpx.Client(transport=httpx.MockTransport(cycle)) as client:
            with self.assertRaises(ValueError):
                s.fetch_all(client,"https://example.org/start")
        self.assertEqual(len(count),1)
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(ValueError):
                s.fetch_all(client,"https://example.org/v1/start",max_pages=1)
            with self.assertRaises(ValueError):
                s.fetch_all(client,"https://example.org/v1/start",max_pages=True)
    """,
    [
        ("relative page links and repeated query parameters", [
            ("navigation.py", "httpx.URL(current).join(link)", "httpx.URL(current).join('/' + link.lstrip('/'))"),
            ("app.py", "params=params if index == 0 else None", "params=params")]),
        ("origin validation and HTTP errors", [
            ("navigation.py", "if (target.scheme, target.host, target.port) != (origin.scheme, origin.host, origin.port):", "if False:"),
            ("app.py", "response.raise_for_status()", "pass")]),
        ("invalid page shape and cycle suppression", [
            ("navigation.py", 'not isinstance(data.get("items"), list)', '"items" not in data'),
            ("app.py", "if identity in seen:", "if False:")]),
        ("invalid next links and page-limit reporting", [
            ("navigation.py", "link is not None and (not isinstance(link, str) or not link)", "False"),
            ("app.py", 'raise ValueError("page limit")', "return values")]),
        ("port isolation and page aggregation", [
            ("navigation.py", "(target.scheme, target.host, target.port) != (origin.scheme, origin.host, origin.port)", "(target.scheme, target.host) != (origin.scheme, origin.host)"),
            ("app.py", "values.extend(items)", "values = items")]),
    ],
    ["https://www.python-httpx.org/advanced/clients/", "https://www.python-httpx.org/compatibility/"],
)

family(
    "settings-api", "mixed",
    """Repair create_app() with Starlette 1.7.0 and HTTPX 0.28.1. GET /settings
returns {value,version}, initially {value:null,version:0}, and quoted ETag.
PUT /settings requires If-Match equal to the current quoted version: missing
header is 428, mismatch is 412. JSON must be exactly {value: string}; malformed
JSON/extra keys/non-string values give 400 and no mutation. A successful PUT
increments the version and returns state plus ETag. The comparison and write
must be atomic. Independent app instances must not share state. Store.update
raises Conflict on mismatched version. Preserve GET behavior after every failed
request, and include an error JSON body on failures.""",
    {
        "state.py": """
            import threading
            class Conflict(Exception):
                pass
            class Store:
                def __init__(self):
                    self.value, self.version = None, 0
                    self.lock = threading.Lock()
                def read(self):
                    with self.lock:
                        return {"value":self.value,"version":self.version}
                def update(self, expected, value):
                    with self.lock:
                        if expected != f'"{self.version}"':
                            raise Conflict()
                        self.value = value
                        self.version += 1
                        return {"value":self.value,"version":self.version}
        """,
        "app.py": """
            import json
            from starlette.applications import Starlette
            from starlette.responses import JSONResponse
            from starlette.routing import Route
            from state import Store, Conflict
            def create_app():
                store = Store()
                async def endpoint(request):
                    if request.method == "GET":
                        data = store.read()
                    else:
                        expected = request.headers.get("if-match")
                        if expected is None:
                            return JSONResponse({"error":"precondition required"},status_code=428)
                        try:
                            body = await request.json()
                        except (ValueError, UnicodeError):
                            return JSONResponse({"error":"invalid json"},status_code=400)
                        if not isinstance(body,dict) or set(body) != {"value"} or not isinstance(body["value"],str):
                            return JSONResponse({"error":"invalid value"},status_code=400)
                        try:
                            data = store.update(expected, body["value"])
                        except Conflict:
                            return JSONResponse({"error":"precondition failed"},status_code=412)
                    return JSONResponse(data,headers={"ETag":f'"{data["version"]}"'})
                return Starlette(routes=[Route("/settings",endpoint,methods=["GET","PUT"])])
        """,
    },
    """
        from starlette.testclient import TestClient
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        with TestClient(s.create_app()) as client:
            initial = client.get("/settings")
            self.assertEqual(initial.json(),{"value":None,"version":0})
            self.assertEqual(initial.headers["etag"],'"0"')
            self.assertEqual(client.put("/settings",json={"value":"a"}).status_code,428)
            for body in ['{','{"value":3}','{"value":"x","extra":1}','[]']:
                bad = client.put("/settings",content=body,headers={"If-Match":'"0"'})
                self.assertEqual(bad.status_code,400)
                self.assertIn("error",bad.json())
            self.assertEqual(client.get("/settings").json(),initial.json())
            ok = client.put("/settings",json={"value":"new"},headers={"If-Match":'"0"'})
            self.assertEqual(ok.status_code,200)
            self.assertEqual(ok.json(),{"value":"new","version":1})
            self.assertEqual(ok.headers["etag"],'"1"')
            for header in ['"0"',"1",'"99"']:
                bad = client.put("/settings",json={"value":"wrong"},headers={"If-Match":header})
                self.assertEqual(bad.status_code,412)
            self.assertEqual(client.get("/settings").json(),ok.json())
        with TestClient(s.create_app()) as client:
            self.assertEqual(client.get("/settings").json(),{"value":None,"version":0})
        store = s.Store()
        barrier = Barrier(6)
        def update(index):
            barrier.wait(timeout=3)
            try:
                store.update('"0"',str(index))
                return True
            except s.Conflict:
                return False
        with ThreadPoolExecutor(max_workers=6) as pool:
            outcomes = list(pool.map(update,range(6)))
        self.assertEqual(sum(outcomes),1)
        self.assertEqual(store.read()["version"],1)
    """,
    [
        ("conditional writes and missing preconditions", [
            ("state.py", 'if expected != f\'"{self.version}"\':', "if False:"),
            ("app.py", "status_code=428", "status_code=400")]),
        ("version increments and error mapping", [
            ("state.py", "self.version += 1", "self.version += 2"),
            ("app.py", "status_code=412", "status_code=409")]),
        ("stored value and ETag formatting", [
            ("state.py", "self.value = value", "self.value = None"),
            ("app.py", 'f\'"{data["version"]}"\'', 'str(data["version"])')]),
        ("quoted version parsing and schema boundaries", [
            ("state.py", 'expected != f\'"{self.version}"\'', "expected != str(self.version)"),
            ("app.py", ' or set(body) != {"value"}', "")]),
        ("read state and successful response body", [
            ("state.py", 'return {"value":self.value,"version":self.version}\n    def update', 'return {"value":None,"version":0}\n    def update'),
            ("app.py", "return JSONResponse(data,headers=", 'return JSONResponse({"ok":True},headers=')]),
    ],
    ["https://www.starlette.io/testclient/", "https://www.starlette.io/responses/",
     "https://www.rfc-editor.org/rfc/rfc9110.html#name-if-match"],
)

family(
    "singleflight", "mixed",
    """Repair Cache(ttl, clock) and Memo across cache_store.py and app.py, using
Python 3.12 asyncio. ttl is positive; clock is injected. Concurrent get(key,loader)
calls coalesce one async loader per key. Values, including None, expire at the
exact ttl boundary, measured at load completion. Loader exceptions propagate to
all waiters and are not cached. Cancelling one waiter must not cancel shared work.
invalidate(key) discards cached/inflight association so a subsequent get starts
fresh work; earlier waiters still receive their own old result, which must not
overwrite a newer value. Memo.get preserves this behavior and Memo.invalidate
delegates. Independent instances and distinct keys must remain independent.""",
    {
        "cache_store.py": """
            import asyncio
            class Cache:
                def __init__(self, ttl, clock):
                    if ttl <= 0:
                        raise ValueError("ttl")
                    self.ttl, self.clock = ttl, clock
                    self.values, self.flights = {}, {}
                async def get(self, key, loader):
                    if key in self.values and self.clock() < self.values[key][0]:
                        return self.values[key][1]
                    task = self.flights.get(key)
                    if task is None:
                        task = asyncio.create_task(self._load(key,loader))
                        self.flights[key] = task
                        task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
                    return await asyncio.shield(task)
                async def _load(self, key, loader):
                    task = asyncio.current_task()
                    try:
                        value = await loader()
                        if self.flights.get(key) is task:
                            self.values[key] = (self.clock() + self.ttl, value)
                        return value
                    finally:
                        if self.flights.get(key) is task:
                            self.flights.pop(key)
                def invalidate(self, key):
                    self.values.pop(key,None)
                    self.flights.pop(key,None)
        """,
        "app.py": """
            from cache_store import Cache
            class Memo:
                def __init__(self, ttl, clock):
                    self.cache = Cache(ttl,clock)
                async def get(self, key, loader):
                    return await self.cache.get(key,loader)
                def invalidate(self, key):
                    self.cache.invalidate(key)
        """,
    },
    """
        import asyncio
        async def check():
            now = [0]
            m = s.Memo(10,lambda:now[0])
            entered, release = asyncio.Event(), asyncio.Event()
            calls = []
            async def load():
                calls.append(1)
                entered.set()
                await release.wait()
                return None
            a = asyncio.create_task(m.get("x",load))
            await entered.wait()
            b = asyncio.create_task(m.get("x",load))
            await asyncio.sleep(0)
            a.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await a
            now[0] = 5
            release.set()
            self.assertIsNone(await b)
            self.assertEqual(len(calls),1)
            async def forbidden():
                raise AssertionError("cached value should be used")
            now[0] = 14
            self.assertIsNone(await m.get("x",forbidden))
            now[0] = 15
            async def fresh():
                return 9
            self.assertEqual(await m.get("x",fresh),9)
            async def fail():
                raise RuntimeError("loader")
            for _ in range(2):
                with self.assertRaises(RuntimeError):
                    await m.get("bad",fail)
            self.assertEqual(await m.get("bad",fresh),9)
            old_started, old_release = asyncio.Event(), asyncio.Event()
            async def old():
                old_started.set()
                await old_release.wait()
                return 1
            pending = asyncio.create_task(m.get("race",old))
            await old_started.wait()
            m.invalidate("race")
            self.assertEqual(await m.get("race",fresh),9)
            old_release.set()
            self.assertEqual(await pending,1)
            self.assertEqual(await m.get("race",forbidden),9)
            m.invalidate("race")
            self.assertEqual(await m.get("race",fresh),9)
            self.assertEqual(await s.Memo(10,lambda:0).get("x",fresh),9)
        asyncio.run(asyncio.wait_for(check(),timeout=4))
        with self.assertRaises(ValueError):
            s.Memo(0,lambda:0)
    """,
    [
        ("waiter cancellation and key forwarding", [
            ("cache_store.py", "return await asyncio.shield(task)", "return await task"),
            ("app.py", "self.cache.get(key,loader)", 'self.cache.get("all",loader)')]),
        ("expiry boundary and invalidation forwarding", [
            ("cache_store.py", "self.clock() < self.values[key][0]", "self.clock() <= self.values[key][0]"),
            ("app.py", "self.cache.invalidate(key)", "pass")]),
        ("inflight invalidation and falsey results", [
            ("cache_store.py", "self.flights.pop(key,None)", "pass"),
            ("app.py", "return await self.cache.get(key,loader)", "return (await self.cache.get(key,loader)) or 0")]),
        ("old load overwrite and TTL forwarding", [
            ("cache_store.py", "if self.flights.get(key) is task:\n                self.values", "if True:\n                self.values"),
            ("app.py", "Cache(ttl,clock)", "Cache(ttl * 2,clock)")]),
        ("error cleanup and repeated invalidation", [
            ("cache_store.py", "self.flights.pop(key)", "pass"),
            ("app.py", "return await self.cache.get(key,loader)", "self.cache.invalidate(key)\n        return await self.cache.get(key,loader)")]),
    ],
    ["https://docs.python.org/3.12/library/asyncio-task.html#shielding-from-cancellation"],
)

family(
    "reporting", "control",
    """This task is entirely specified locally; external documentation is not
needed. Repair build_report(records) across app.py and formatting.py. Each record
has team (nonempty after stripping), name (string), and minutes (exact nonnegative
int). Raise ValueError for invalid records without mutating input. Group by
stripped, casefolded team; sum minutes and count records. Return CSV text with
header team,count,minutes and LF line endings. Sort by descending total minutes,
then normalized team ascending. CSV quote commas, quotes and newlines correctly.
Empty input returns just the header. Existing helper normalize and emit remain
public. Records with minutes=0 still count; names are validated but not emitted.""",
    {
        "formatting.py": """
            import csv
            import io
            def normalize(record):
                team, name, minutes = record["team"], record["name"], record["minutes"]
                if not isinstance(team,str) or not team.strip() or not isinstance(name,str):
                    raise ValueError("text")
                if type(minutes) is not int or minutes < 0:
                    raise ValueError("minutes")
                return team.strip().casefold(), minutes
            def emit(rows):
                stream = io.StringIO(newline="")
                writer = csv.writer(stream,lineterminator="\\n")
                writer.writerow(["team","count","minutes"])
                writer.writerows(rows)
                return stream.getvalue()
        """,
        "app.py": """
            from formatting import normalize, emit
            def build_report(records):
                totals = {}
                for record in records:
                    team, minutes = normalize(record)
                    count, total = totals.get(team,(0,0))
                    totals[team] = count + 1, total + minutes
                ordered = sorted(totals,key=lambda team:(-totals[team][1],team))
                return emit([(team,*totals[team]) for team in ordered])
        """,
    },
    """
        import csv
        import io
        from copy import deepcopy
        records = [{"team":" Beta ","name":"b","minutes":5},{"team":"BETA","name":"c","minutes":0},
                   {"team":"alpha","name":"x","minutes":5},{"team":'a,"b\\nc',"name":"","minutes":1}]
        before = deepcopy(records)
        output = s.build_report(records)
        self.assertEqual(list(csv.reader(io.StringIO(output))),
                         [["team","count","minutes"],["alpha","1","5"],["beta","2","5"],['a,"b\\nc',"1","1"]])
        self.assertEqual(records,before)
        self.assertNotIn("\\r",output)
        self.assertEqual(s.build_report([]),"team,count,minutes\\n")
        for field, value in [("team"," "),("team",3),("name",None),("minutes",True),
                             ("minutes",-1),("minutes","3")]:
            with self.assertRaises(ValueError):
                s.build_report([dict(records[0],**{field:value})])
        self.assertEqual(s.build_report([{"team":"z","name":"a","minutes":2},
                                        {"team":"a","name":"a","minutes":1}]),
                         "team,count,minutes\\nz,1,2\\na,1,1\\n")
    """,
    [
        ("normalization and stable ties", [
            ("formatting.py", "team.strip().casefold()", "team.strip()"),
            ("app.py", "(-totals[team][1],team)", "(-totals[team][1],)")]),
        ("strict minutes and zero-value counting", [
            ("formatting.py", "type(minutes) is not int", "not isinstance(minutes,int)"),
            ("app.py", "count + 1, total + minutes", "count + bool(minutes), total + minutes")]),
        ("CSV newline convention and sort direction", [
            ("formatting.py", 'lineterminator="\\n"', 'lineterminator="\\r\\n"'),
            ("app.py", "(-totals[team][1],team)", "(totals[team][1],team)")]),
        ("name validation and aggregation", [
            ("formatting.py", " or not isinstance(name,str)", ""),
            ("app.py", "count + 1, total + minutes", "count + 1, minutes")]),
        ("whitespace-only team and row shape", [
            ("formatting.py", "not team.strip()", "not team"),
            ("app.py", "(team,*totals[team])", "(team,totals[team][1],totals[team][0])")]),
    ],
)

family(
    "catalog", "control",
    """This task needs only the supplied local contract, not external knowledge.
Repair select(items, config) and render(items, config) across app.py and rules.py.
Each item has unique string id, string label, integer priority, boolean enabled,
and list[str] tags. Configuration includes required_tags (list[str], default []),
include_disabled (bool, default False), and limit (nonnegative exact int or None).
Validate all items and config, including items that would be filtered out;
unknown config keys are ValueError. Selection requires all requested tags,
excludes disabled unless requested, sorts priority descending then id ascending,
and applies limit after filtering/sorting. Return deep copies preserving input
order/data. render returns selected labels joined by ' | ', escaping backslash
as double backslash and pipe as backslash-pipe; empty selection returns '(none)'.
Duplicate ids and malformed data raise ValueError.""",
    {
        "rules.py": """
            def validate(items, config):
                if set(config) - {"required_tags","include_disabled","limit"}:
                    raise ValueError("unknown option")
                tags = config.get("required_tags",[])
                enabled = config.get("include_disabled",False)
                limit = config.get("limit")
                if not isinstance(tags,list) or any(not isinstance(t,str) for t in tags) or type(enabled) is not bool:
                    raise ValueError("config")
                if limit is not None and (type(limit) is not int or limit < 0):
                    raise ValueError("limit")
                seen = set()
                for item in items:
                    if (not isinstance(item.get("id"),str) or not isinstance(item.get("label"),str)
                            or type(item.get("priority")) is not int or type(item.get("enabled")) is not bool
                            or not isinstance(item.get("tags"),list)
                            or any(not isinstance(t,str) for t in item["tags"])):
                        raise ValueError("item")
                    if item["id"] in seen:
                        raise ValueError("duplicate")
                    seen.add(item["id"])
                return set(tags), enabled, limit
            def escape(label):
                return label.replace("\\\\","\\\\\\\\").replace("|","\\\\|")
        """,
        "app.py": """
            from copy import deepcopy
            from rules import validate, escape
            def select(items, config):
                tags, include_disabled, limit = validate(items,config)
                chosen = [item for item in items if (item["enabled"] or include_disabled)
                          and tags <= set(item["tags"])]
                chosen.sort(key=lambda item:(-item["priority"],item["id"]))
                return deepcopy(chosen[:limit])
            def render(items, config):
                selected = select(items,config)
                return " | ".join(escape(item["label"]) for item in selected) if selected else "(none)"
        """,
    },
    """
        from copy import deepcopy
        items = [{"id":"b","label":"B|x","priority":2,"enabled":True,"tags":["x","y"]},
                 {"id":"a","label":"A\\\\x","priority":2,"enabled":True,"tags":["x"]},
                 {"id":"c","label":"C","priority":9,"enabled":False,"tags":["x","y"]}]
        before = deepcopy(items)
        self.assertEqual([i["id"] for i in s.select(items,{})],["a","b"])
        self.assertEqual([i["id"] for i in s.select(items,{"required_tags":["x","y"]})],["b"])
        self.assertEqual([i["id"] for i in s.select(items,{"include_disabled":True,"limit":1})],["c"])
        self.assertEqual(s.render(items,{}),"A\\\\\\\\x | B\\\\|x")
        self.assertEqual(s.render(items,{"limit":0}),"(none)")
        selected = s.select(items,{})
        selected[0]["tags"].append("changed")
        self.assertEqual(items,before)
        for config in [{"limit":True},{"limit":-1},{"limit":"1"},{"include_disabled":1},
                       {"required_tags":"x"},{"required_tags":[1]},{"extra":1}]:
            with self.assertRaises(ValueError):
                s.select(items,config)
        for patch in [{"id":"a"},{"priority":True},{"enabled":0},{"tags":[1]},{"label":None}]:
            bad = deepcopy(items)
            bad[2].update(patch)
            with self.assertRaises(ValueError):
                s.select(bad,{"limit":0})
        self.assertEqual(s.select([],{}),[])
    """,
    [
        ("all-tag matching and unknown options", [
            ("rules.py", 'if set(config) - {"required_tags","include_disabled","limit"}:', "if False:"),
            ("app.py", 'tags <= set(item["tags"])', '(not tags or bool(tags & set(item["tags"])))')]),
        ("strict limits and zero-limit behavior", [
            ("rules.py", "type(limit) is not int", "not isinstance(limit,int)"),
            ("app.py", "chosen[:limit]", "chosen[:limit or None]")]),
        ("duplicate detection and copy ownership", [
            ("rules.py", 'if item["id"] in seen:', "if False:"),
            ("app.py", "return deepcopy(chosen[:limit])", "return chosen[:limit]")]),
        ("escaping and priority order", [
            ("rules.py", 'return label.replace("\\\\","\\\\\\\\").replace("|","\\\\|")', "return label"),
            ("app.py", '(-item["priority"],item["id"])', '(item["priority"],item["id"])')]),
        ("disabled validation and empty rendering", [
            ("rules.py", 'or type(item.get("enabled")) is not bool', ""),
            ("app.py", 'else "(none)"', 'else ""')]),
    ],
)
