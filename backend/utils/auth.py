import os
import time
import hashlib
import secrets
import base64
from typing import Optional, Tuple, Dict, Any

try:
    import jwt  # PyJWT
    HAS_JWT = True
except Exception:
    HAS_JWT = False

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def get_or_generate_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if secret:
        return secret
    # Only auto-generate in dev
    if os.getenv("APP_ENV", "development") == "development":
        # Use a fixed fallback secret for development to persist across restarts
        # if not explicitly set in .env
        jwk = "dev_secret_do_not_use_in_prod_learnlab_12345"
        print("[WARN] No JWT_SECRET set, using fixed dev secret:", jwk)
        os.environ["JWT_SECRET"] = jwk
        return jwk
    raise RuntimeError("JWT_SECRET must be set in production!")

JWT_SECRET = get_or_generate_jwt_secret()
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")
JWT_ISSUER = os.getenv("JWT_ISSUER")
ACCESS_TOKEN_EX = int(os.getenv("ACCESS_TOKEN_EX", "3600"))  # 1h
REFRESH_TOKEN_EX = int(os.getenv("REFRESH_TOKEN_EX", "1209600"))  # 14d

API_KEY = os.getenv("API_KEY", "")
# Default to True if not specified, to ensure secure-by-default
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "1") == "1"

class AuthError(Exception):
    pass

# Password hashing

def hash_password(pw: str) -> str:
    return pwd_context.hash(pw)

def verify_password(pw: str, pw_hash: str) -> bool:
    try:
        return pwd_context.verify(pw, pw_hash)
    except Exception:
        return False

# JWT helpers

def create_access_token(user_id: str, email: str, scopes: list[str], roles: list[str]) -> str:
    if not HAS_JWT:
        raise AuthError("JWT not available")
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email.lower(),
        "scopes": scopes,
        "roles": roles,
        "iat": now,
        "exp": now + ACCESS_TOKEN_EX,
    }
    if JWT_AUDIENCE: payload["aud"] = JWT_AUDIENCE
    if JWT_ISSUER: payload["iss"] = JWT_ISSUER
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def create_refresh_token(user_id: str, email: str) -> str:
    if not HAS_JWT:
        raise AuthError("JWT not available")
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email.lower(),
        "type": "refresh",
        "iat": now,
        "exp": now + REFRESH_TOKEN_EX,
    }
    if JWT_AUDIENCE: payload["aud"] = JWT_AUDIENCE
    if JWT_ISSUER: payload["iss"] = JWT_ISSUER
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> Dict[str, Any]:
    if not HAS_JWT:
        raise AuthError("JWT not available")
    opts = {"verify_aud": bool(JWT_AUDIENCE)}
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"], audience=JWT_AUDIENCE, issuer=JWT_ISSUER, options=opts)

# API key or JWT check

def verify_api_key_or_jwt(api_key: Optional[str], bearer: Optional[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    if not AUTH_REQUIRED:
        return True, None
    # API key
    if API_KEY and api_key and api_key == API_KEY:
        return True, {"method": "api_key"}
    # JWT
    if bearer and bearer.lower().startswith("bearer "):
        token = bearer.split(" ", 1)[1].strip()
        try:
            claims = decode_token(token)
            return True, {"method": "jwt", "claims": claims}
        except Exception as e:
            raise AuthError(str(e))
    raise AuthError("Unauthorized")

# Refresh token persistence helpers

def hash_refresh_token(rt: str) -> str:
    return hashlib.sha256(rt.encode("utf-8")).hexdigest()

# FastAPI dependency for getting current user

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(credentials = Depends(security)) -> Dict[str, Any]:
    """
    FastAPI dependency to extract current user from JWT token.
    Returns user dict with id and email.
    """
    try:
        token = credentials.credentials
        claims = decode_token(token)
        return {
            "user_id": claims.get("sub"),
            "email": claims.get("email"),
            "scopes": claims.get("scopes", []),
            "roles": claims.get("roles", []),
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid credentials: {str(e)}")
