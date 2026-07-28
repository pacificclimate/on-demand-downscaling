"""Short-lived, single-use email authentication codes backed by Redis."""

from dataclasses import dataclass
import hashlib
import hmac
import os
import secrets

from redis.exceptions import WatchError

KEY_PREFIX = "odds:one-time-auth"
ONE_TIME_AUTH_CODE_DIGITS = int(os.getenv("ONE_TIME_AUTH_CODE_DIGITS", "6"))
ONE_TIME_AUTH_TOKEN_TTL_SECONDS = int(
    os.getenv("ONE_TIME_AUTH_TOKEN_TTL_SECONDS", "600")
)
ONE_TIME_AUTH_RESEND_SECONDS = int(os.getenv("ONE_TIME_AUTH_RESEND_SECONDS", "60"))
ONE_TIME_AUTH_MAX_ATTEMPTS = int(os.getenv("ONE_TIME_AUTH_MAX_ATTEMPTS", "5"))
ONE_TIME_AUTH_ACCESS_TTL_SECONDS = int(
    os.getenv("ONE_TIME_AUTH_ACCESS_TTL_SECONDS", "28800")
)


class OneTimeAuthRateLimited(Exception):
    """Raised when another code was requested too recently for an email."""


@dataclass(frozen=True)
class OneTimeChallenge:
    challenge_id: str
    code: str
    email: str


@dataclass(frozen=True)
class VerificationResult:
    status: str
    email: str | None = None


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _email_fingerprint(email: str) -> str:
    return hashlib.sha256(normalize_email(email).encode("utf-8")).hexdigest()


def _challenge_key(challenge_id: str) -> str:
    return f"{KEY_PREFIX}:challenge:{challenge_id}"


def _rate_key(email: str) -> str:
    return f"{KEY_PREFIX}:rate:{_email_fingerprint(email)}"


def _digest_code(salt: str, code: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()


def create_challenge(redis_client, email: str) -> OneTimeChallenge:
    """Create and persist a code, returning the plaintext only for email delivery."""
    normalized_email = normalize_email(email)
    rate_key = _rate_key(normalized_email)
    allowed = redis_client.set(
        rate_key, "1", nx=True, ex=ONE_TIME_AUTH_RESEND_SECONDS
    )
    if not allowed:
        raise OneTimeAuthRateLimited

    challenge_id = secrets.token_urlsafe(32)
    code = f"{secrets.randbelow(10 ** ONE_TIME_AUTH_CODE_DIGITS):0{ONE_TIME_AUTH_CODE_DIGITS}d}"
    salt = secrets.token_hex(16)
    key = _challenge_key(challenge_id)

    try:
        pipe = redis_client.pipeline()
        pipe.hset(
            key,
            mapping={
                "email": normalized_email,
                "salt": salt,
                "digest": _digest_code(salt, code),
                "attempts": 0,
            },
        )
        pipe.expire(key, ONE_TIME_AUTH_TOKEN_TTL_SECONDS)
        pipe.execute()
    except Exception:
        redis_client.delete(rate_key)
        raise

    return OneTimeChallenge(challenge_id, code, normalized_email)


def revoke_challenge(redis_client, challenge: OneTimeChallenge) -> None:
    """Remove a challenge and its throttle, primarily when email delivery fails."""
    redis_client.delete(
        _challenge_key(challenge.challenge_id), _rate_key(challenge.email)
    )


def _decode_hash(data) -> dict[str, str]:
    return {
        (key.decode("utf-8") if isinstance(key, bytes) else str(key)): (
            value.decode("utf-8") if isinstance(value, bytes) else str(value)
        )
        for key, value in data.items()
    }


def verify_challenge(redis_client, challenge_id: str, code: str) -> VerificationResult:
    """Atomically consume a valid code or count a failed attempt."""
    if not challenge_id:
        return VerificationResult("expired")

    key = _challenge_key(challenge_id)
    supplied_code = (code or "").strip()

    while True:
        pipe = redis_client.pipeline()
        try:
            pipe.watch(key)
            raw = pipe.hgetall(key)
            if not raw:
                return VerificationResult("expired")

            data = _decode_hash(raw)
            attempts = int(data.get("attempts", "0"))
            expected = data.get("digest", "")
            actual = _digest_code(data.get("salt", ""), supplied_code)

            pipe.multi()
            if hmac.compare_digest(expected, actual):
                pipe.delete(key)
                pipe.execute()
                return VerificationResult("verified", data.get("email"))

            attempts += 1
            if attempts >= ONE_TIME_AUTH_MAX_ATTEMPTS:
                pipe.delete(key)
                status = "too_many_attempts"
            else:
                pipe.hset(key, "attempts", attempts)
                status = "invalid"
            pipe.execute()
            return VerificationResult(status)
        except WatchError:
            continue
        finally:
            pipe.reset()
