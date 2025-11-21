import os
from typing import List

SECRETS_DIR = os.getenv("SECRETS_DIR", "/run/secrets")

# Keys to load from Docker secrets if not set in env
DEFAULT_SECRET_KEYS: List[str] = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "JWT_SECRET",
]

def load_docker_secrets(keys: List[str] = DEFAULT_SECRET_KEYS) -> None:
    if not os.path.isdir(SECRETS_DIR):
        return
    for key in keys:
        if os.getenv(key):
            continue
        path = os.path.join(SECRETS_DIR, key)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    value = f.read().strip()
                    if value:
                        os.environ[key] = value
            except Exception:
                pass
