import hashlib
import hmac
import os
import secrets
import time
from typing import Optional

import jwt

# 与前端 lib/password.ts 保持兼容：scryptSync(password, salt, 64)，格式 "salt:hash"（hex）
KEY_LENGTH = 64
# Python 的 scrypt 需要显式放宽内存上限（128 * N * r ≈ 16MB，留足余量）
SCRYPT_MAXMEM = 64 * 1024 * 1024

# 登录会话：HttpOnly Cookie 承载的 JWT
SESSION_COOKIE = "cb_token"
SESSION_TTL_SECONDS = 7 * 24 * 3600  # 7 天


def _auth_secret() -> bytes:
    secret = os.getenv("AUTH_SECRET")
    if secret:
        return secret.encode()
    # 未配置 AUTH_SECRET 时退回进程级随机密钥：开发期可用，
    # 但服务重启后全部会话失效；生产环境必须显式配置（Vercel 环境变量）
    return secrets.token_bytes(32)


def create_session_token(account: dict) -> str:
    """登录成功后签发会话 JWT：sub = accounts.id（UUID 字符串）。"""
    now = int(time.time())
    payload = {
        "sub": str(account["id"]),
        "email": account.get("email"),
        "name": account.get("name"),
        "iat": now,
        "exp": now + SESSION_TTL_SECONDS,
    }
    return jwt.encode(payload, _auth_secret(), algorithm="HS256")


def decode_session_token(token: str) -> Optional[dict]:
    """验证并解析会话 JWT；无效 / 过期返回 None。"""
    try:
        return jwt.decode(token, _auth_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived = hashlib.scrypt(
        password.encode(),
        salt=salt.encode(),
        n=16384,
        r=8,
        p=1,
        dklen=KEY_LENGTH,
        maxmem=SCRYPT_MAXMEM,
    )
    return f"{salt}:{derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected_hex = stored.split(":", 1)
    except ValueError:
        return False
    derived = hashlib.scrypt(
        password.encode(),
        salt=salt.encode(),
        n=16384,
        r=8,
        p=1,
        dklen=KEY_LENGTH,
        maxmem=SCRYPT_MAXMEM,
    )
    return hmac.compare_digest(derived.hex(), expected_hex)


def generate_verification_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"
