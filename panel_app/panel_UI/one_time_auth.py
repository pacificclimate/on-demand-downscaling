"""Short-lived, single-use email authentication codes backed by Redis."""

from dataclasses import dataclass
import hashlib
import hmac
import math
import os
import secrets
from time import time

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
ONE_TIME_AUTH_JOB_LIMIT = int(os.getenv("ONE_TIME_AUTH_JOB_LIMIT", "2"))
ONE_TIME_AUTH_JOB_WINDOW_SECONDS = int(
    os.getenv("ONE_TIME_AUTH_JOB_WINDOW_SECONDS", "86400")
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


@dataclass(frozen=True)
class JobQuotaDecision:
    allowed: bool
    reservation_id: str | None = None
    retry_after_seconds: int = 0


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _email_fingerprint(email: str) -> str:
    return hashlib.sha256(normalize_email(email).encode("utf-8")).hexdigest()


def _challenge_key(challenge_id: str) -> str:
    return f"{KEY_PREFIX}:challenge:{challenge_id}"


def _rate_key(email: str) -> str:
    return f"{KEY_PREFIX}:rate:{_email_fingerprint(email)}"


def _job_quota_key(email: str) -> str:
    return f"{KEY_PREFIX}:jobs:{_email_fingerprint(email)}"


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


def reserve_job_submission(
    redis_client, email: str, now: float | None = None
) -> JobQuotaDecision:
    """Atomically reserve one slot in the email's rolling job window."""
    current_time = time() if now is None else now
    cutoff = current_time - ONE_TIME_AUTH_JOB_WINDOW_SECONDS
    key = _job_quota_key(email)

    while True:
        pipe = redis_client.pipeline()
        try:
            pipe.watch(key)
            submissions = pipe.zrange(key, 0, -1, withscores=True)
            active = [item for item in submissions if item[1] > cutoff]

            if len(active) >= ONE_TIME_AUTH_JOB_LIMIT:
                earliest = min(score for _, score in active)
                retry_after = max(
                    1,
                    math.ceil(
                        earliest + ONE_TIME_AUTH_JOB_WINDOW_SECONDS - current_time
                    ),
                )
                return JobQuotaDecision(False, retry_after_seconds=retry_after)

            reservation_id = secrets.token_urlsafe(18)
            expired = [member for member, score in submissions if score <= cutoff]
            pipe.multi()
            if expired:
                pipe.zrem(key, *expired)
            pipe.zadd(key, {reservation_id: current_time})
            pipe.expire(key, ONE_TIME_AUTH_JOB_WINDOW_SECONDS + 60)
            pipe.execute()
            return JobQuotaDecision(True, reservation_id=reservation_id)
        except WatchError:
            continue
        finally:
            pipe.reset()


def release_job_reservation(redis_client, email: str, reservation_id: str) -> None:
    """Return a reserved slot when enqueueing fails before a job is created."""
    if reservation_id:
        redis_client.zrem(_job_quota_key(email), reservation_id)
