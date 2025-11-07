import os
import sys
import redis
from rq import Worker, Queue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panel_app.panel_UI.tasks import process_odds_job


redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
conn = redis.from_url(redis_url)

if __name__ == "__main__":
    q = Queue(connection=conn)
    worker = Worker([q])
    worker.work()
