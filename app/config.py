import os

SECRET_KEY = os.environ.get("SECRET_KEY", "TU_SECRET_KEY_TEMPORAL")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = float(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# Default to local SQLite for dev/tests; override via env in Docker/Prod
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./taskmaster.db")
