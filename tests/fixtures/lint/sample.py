import requests
import asyncio


def fetch_data(url):
    # BPM-L003: requests without timeout
    resp = requests.get(url)
    return resp.json()


def fetch_with_timeout(url):
    # Should NOT trigger BPM-L003 (has timeout)
    resp = requests.get(url, timeout=10)
    return resp.json()


async def async_handler(request):
    # BPM-L004: sync requests in async function
    data = requests.post("http://api.example.com/data", json={"key": "value"})
    return data.json()


def risky_eval(user_input):
    # BPM-L015: eval usage
    return eval(user_input)


def run_query(db, user_id):
    # BPM-L016: string interpolation in SQL
    db.execute(f"SELECT * FROM users WHERE id = {user_id}")


try:
    pass
except:  # BPM-L010: bare except
    pass


def get_token():
    jwt_secret = "super-secret-key-12345"  # BPM-L017: hardcoded JWT secret
    return jwt_secret
