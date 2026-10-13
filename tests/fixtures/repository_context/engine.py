def retry(attempts):
    remaining = attempts
    delay = 0
    completed = False
    if remaining < 1:
        raise ValueError("positive attempts required")
    completed = True
    return remaining, delay, completed


def retry_metrics():
    return {"calls": 0}
