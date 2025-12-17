
# run_simple_worker.py
import logging
import os
import time
from typing import NoReturn

from redis import Redis
from rq import Queue, SimpleWorker

from app.config import get_settings  # <- CORRIGÉ : config (sans s)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
)

# Chargement des settings (Pydantic / BaseSettings)
settings = get_settings()


def create_redis_connection() -> Redis:
    """
    Crée et retourne une connexion Redis à partir de REDIS_URL.
    Lève une exception si la connexion échoue.
    """
    redis_url = str(settings.REDIS_URL)
    logging.info("Connecting to Redis at %s", redis_url)
    conn = Redis.from_url(redis_url)

    # Test rapide de la connexion
    try:
        conn.ping()
    except Exception as exc:  # noqa: BLE001
        logging.exception("Unable to connect to Redis: %s", exc)
        raise

    logging.info("Redis connection established successfully.")
    return conn


def create_worker(redis_conn: Redis) -> SimpleWorker:
    """
    Crée un worker RQ sur la file configurée.
    Le nom de la file peut être surchargé via la variable d'env QUEUE_NAME.
    """
    queue_name = os.getenv("QUEUE_NAME", "default")
    logging.info("Using RQ queue: %s", queue_name)

    queue = Queue(queue_name, connection=redis_conn)
    worker = SimpleWorker([queue], connection=redis_conn)

    return worker


def run_worker_forever(worker: SimpleWorker) -> NoReturn:
    """
    Boucle principale du worker.
    Redémarre le worker en cas d'exception après une courte pause.
    """
    logging.info("Starting RQ SimpleWorker loop...")

    while True:
        try:
            # burst=False => le worker reste en écoute en continu
            worker.work(burst=False)
        except Exception as exc:  # noqa: BLE001
            logging.exception("Worker error: %s", exc)
            logging.info("Worker will restart in 5 seconds...")
            time.sleep(5)


def main() -> None:
    logging.info("Bootstrapping worker process...")

    redis_conn = create_redis_connection()
    worker = create_worker(redis_conn)

    run_worker_forever(worker)


if __name__ == "__main__":
    main()
