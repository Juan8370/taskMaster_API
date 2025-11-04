from datetime import datetime, timedelta, UTC
from jose import jwt
from passlib.context import CryptContext
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    """Hash a password after validating bcrypt's 72-byte limit.

    Raises ValueError if the UTF-8 encoding of the password exceeds 72 bytes.
    """
    if isinstance(password, str):
        b = password.encode("utf-8")
        if len(b) > 72:
            # make the failure explicit and consistent
            raise ValueError("password too long: must be at most 72 bytes when UTF-8 encoded")
    return pwd_context.hash(password)


def verify_password(plain, hashed):
    """Verify a plaintext password against a hash.

    If verification raises a ValueError (for example plain >72 bytes), return False
    to allow the caller to respond with an authentication failure instead of an error.
    """
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        return False

def create_token(data: dict):
    data = data.copy()
    # read expiry at call-time so tests (and runtime overrides) that modify
    # app.config.ACCESS_TOKEN_EXPIRE_MINUTES take effect immediately
    import app.config as _cfg
    expire = datetime.now(UTC) + timedelta(minutes=_cfg.ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": int(expire.timestamp())})  # JWT spec uses Unix timestamp
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
