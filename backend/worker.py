import os
from redis import Redis  # type: ignore
from rq import Worker, Queue, Connection  # type: ignore

listen = [os.getenv("RQ_QUEUE", "learnlab")]
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

if __name__ == '__main__':
    conn = Redis.from_url(redis_url)
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()
