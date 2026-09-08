"""Atomic, cross-worker run locks backed by Redis (via frappe.cache()).

Acquire uses `SET key token NX EX ttl` — atomic, and self-healing when a worker
dies (the TTL expires, so a crashed job can never wedge a page/session forever).
The returned token FENCES release: a worker that outlived its TTL can no longer
delete the lock a newer holder acquired (release compares the token in Redis).

`frappe.cache()` is a `redis.Redis` subclass, so the raw `.set(nx=, ex=)` is used
directly for atomicity (the `set_value` helper has no NX flag). `make_key` scopes
every lock to the current site.

Generic enough to upstream as a `frappe.cache().lock(...)` primitive; Builder is
the first consumer.
"""

import secrets
import threading
from contextlib import contextmanager

import frappe

# TTLs sit just above each holder's job timeout so a dead worker's lock expires
# on its own. Page and session locks are held by chat turns (timeout 600s); task
# locks by a fan-out sub-agent (timeout 780s).
PAGE_LOCK_TTL = 660
TASK_LOCK_TTL = 840
SESSION_LOCK_TTL = 660


# //// Neoffice — added. A Nora site build runs INSIDE the chat turn (generate_site, 15 to
# //// 25 minutes) while the TTLs above fit upstream's 10-minute turns. Longer TTLs were the
# //// first answer and a trap: a lock left behind by a killed worker (bench restart mid-build)
# //// then blocks the page for an hour. Instead the running turn renews its locks from a
# //// daemon thread: a live turn keeps them for as long as it runs, a dead one lets them
# //// expire within the TTL, exactly as upstream intends.
EXTEND_IF_TOKEN_MATCHES = """
if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('expire', KEYS[1], ARGV[2]) end
return 0
"""


class Heartbeat:
	"""Renews the locks a turn holds, from a daemon thread, while the turn runs.

	Keys are resolved (`make_key`) on the calling thread: `frappe.local` is thread-local
	and unbound in the worker thread. The redis client itself is a connection pool and
	safe to use from there. `stop()` is idempotent; a thread never started is a no-op."""

	def __init__(self, every: float | None = None):
		self._client = frappe.cache()
		self._pairs: list[tuple[bytes | str, str, int]] = []
		self._every = every
		self._stop = threading.Event()
		self._thread: threading.Thread | None = None

	def watch(self, key: str, token: str | None, ttl: int) -> None:
		if not token:
			return
		self._pairs.append((self._client.make_key(key), token, ttl))
		if self._thread is None:
			self._thread = threading.Thread(target=self._run, name="builder-ai-lock-heartbeat", daemon=True)
			self._thread.start()

	def stop(self) -> None:
		self._stop.set()
		if self._thread is not None:
			self._thread.join(timeout=2)

	def _run(self) -> None:
		every = self._every or max(5, min(ttl for _, _, ttl in self._pairs) // 4)
		while not self._stop.wait(every):
			for made_key, token, ttl in list(self._pairs):
				try:
					self._client.eval(EXTEND_IF_TOKEN_MATCHES, 1, made_key, token, ttl)
				except Exception:
					pass

RELEASE_IF_TOKEN_MATCHES = """
if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) end
return 0
"""


def page_key(page_id: str) -> str:
	return f"builder_ai_page_lock:{page_id}"


def task_key(task_id: str) -> str:
	"""Lock for a page-less fan-out task (page-backed tasks use page_key instead)."""
	return f"builder_ai_task_lock:{task_id}"


def session_key(session_id: str) -> str:
	"""One running turn per chat session (replaces the old is_running DB flag,
	which was a non-atomic check-then-set and needed manual repair after a crash)."""
	return f"builder_ai_session_lock:{session_id}"


def acquire(key: str, ttl: int) -> str | None:
	"""Atomically acquire `key`. Returns the release token, or None if already held."""
	token = secrets.token_hex(8)
	# make_key scopes the key to the current site, so this is multi-tenant safe; the
	# raw client is required because set_value has no NX flag (see module docstring).
	cache = frappe.cache()  # nosemgrep
	return token if cache.set(cache.make_key(key), token, nx=True, ex=ttl) else None


def release(key: str, token: str | None) -> None:
	"""Release `key` only if we still hold it (token match) — never a newer holder's lock."""
	if not token:
		return
	cache = frappe.cache()
	cache.eval(RELEASE_IF_TOKEN_MATCHES, 1, cache.make_key(key), token)


def held(key: str) -> bool:
	# RedisWrapper.exists applies make_key itself — prefixing here double-scopes
	# the key and the check always misses.
	return bool(frappe.cache().exists(key))


@contextmanager
def guard(key: str, ttl: int):
	"""Yield the lock token (None if not acquired), releasing on exit:

	with guard(page_key(pid), PAGE_LOCK_TTL) as got:
	    if not got:
	        return  # someone else is already running this
	    ...work...
	"""
	token = acquire(key, ttl)
	try:
		yield token
	finally:
		release(key, token)
