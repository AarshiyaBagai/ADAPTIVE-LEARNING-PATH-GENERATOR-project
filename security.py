"""Password hashing and signed tokens, standard library only.

Passwords: PBKDF2-HMAC-SHA256 with a random per-user salt.
Tokens: HS256 JWT (header.payload.signature), compatible with any JWT library.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

PBKDF2_ITERATIONS = int(os.environ.get("ALPG_PBKDF2_ITERATIONS", "200000"))
TOKEN_TTL_SECONDS = int(os.environ.get("ALPG_TOKEN_TTL", str(8 * 3600)))


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ---------- passwords ----------
def hash_password(password: str, iterations: int = None) -> str:
    iterations = iterations or PBKDF2_ITERATIONS
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64e(salt)}${_b64e(dk)}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check. Hashes that do not parse (e.g. '!' = login disabled) never match."""
    try:
        algo, iters, salt, expected = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _b64d(salt), int(iters))
        return hmac.compare_digest(dk, _b64d(expected))
    except (ValueError, TypeError):
        return False


# A real hash of a random value, used to spend the same time when the email is unknown
# (so response time does not reveal which emails exist).
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


# ---------- tokens ----------
def get_secret(data_dir: str) -> bytes:
    """Use ALPG_SECRET if set, otherwise create and reuse a random key file (mode 600)."""
    env = os.environ.get("ALPG_SECRET")
    if env:
        return env.encode("utf-8")
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, ".secret")
    if not os.path.exists(path):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip().encode("utf-8")


def make_token(secret: bytes, user_id: int, role: str, now: float = None) -> str:
    now = int(now if now is not None else time.time())
    header = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64e(json.dumps({"sub": str(user_id), "role": role, "iat": now, "exp": now + TOKEN_TTL_SECONDS},
                               separators=(",", ":")).encode())
    sig = hmac.new(secret, f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64e(sig)}"


def read_token(secret: bytes, token: str, now: float = None):
    """Return the payload dict, or None if the token is malformed, tampered with or expired."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        header = json.loads(_b64d(header_b64))
        if header.get("alg") != "HS256":  # rejects alg=none and algorithm-confusion tricks
            return None
        expected = hmac.new(secret, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64d(sig_b64)):
            return None
        payload = json.loads(_b64d(payload_b64))
        if int(payload["exp"]) < int(now if now is not None else time.time()):
            return None
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
