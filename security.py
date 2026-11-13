import hashlib
import hmac
import secrets

# 与前端 lib/password.ts 保持兼容：scryptSync(password, salt, 64)，格式 "salt:hash"（hex）
KEY_LENGTH = 64
# Python 的 scrypt 需要显式放宽内存上限（128 * N * r ≈ 16MB，留足余量）
SCRYPT_MAXMEM = 64 * 1024 * 1024


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
