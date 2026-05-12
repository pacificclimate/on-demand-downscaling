import json
import os

import redis
import requests
from tornado.web import RequestHandler


SERVICE_CHECK_TIMEOUT = int(os.getenv("READYZ_TIMEOUT_SECONDS", "5"))


def _check_magpie_status():
    magpie_url = os.getenv("MAGPIE_URL")
    if not magpie_url:
        raise ValueError("MAGPIE_URL is not configured.")

    resp = requests.get(
        f"{magpie_url}/session",
        timeout=SERVICE_CHECK_TIMEOUT,
        allow_redirects=False,
    )
    if resp.status_code >= 500:
        resp.raise_for_status()

    return {
        "ok": True,
        "label": "Magpie",
        "detail": f"Magpie session endpoint reachable ({resp.status_code})",
    }


def _check_queue_status():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = redis.from_url(redis_url)
    client.ping()
    return {"ok": True, "label": "Queue", "detail": "Redis queue reachable"}


def collect_ready_status():
    checks = {
        "magpie": _check_magpie_status,
        "queue": _check_queue_status,
    }
    status = {}
    for key, check in checks.items():
        try:
            status[key] = check()
        except Exception as exc:
            label = key.capitalize() if key != "queue" else "Queue"
            status[key] = {"ok": False, "label": label, "detail": str(exc)}
    return status


class ReadyzHandler(RequestHandler):
    def get(self):
        status = collect_ready_status()
        ready = all(item["ok"] for item in status.values())

        self.set_header("Content-Type", "application/json")
        self.set_status(200 if ready else 503)
        self.finish(
            json.dumps(
                {
                    "ready": ready,
                    "checks": status,
                }
            )
        )


ROUTES = [(r"/readyz", ReadyzHandler, {})]
