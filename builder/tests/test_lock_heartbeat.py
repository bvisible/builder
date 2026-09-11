# //// Neoffice — added file (no upstream equivalent): a running turn keeps its lock.
import time
import unittest

import frappe

from builder.ai import locks


class TestHeartbeat(unittest.TestCase):
	"""Against the site's real Redis: the lock is a Redis key, and what failed was Redis-side."""

	def test_a_deleted_lock_comes_back_under_the_same_token(self):
		"""The session lock of a site build vanished in the middle of its visual check, and
		the panel's watchdog read the turn as over while the job was still building."""
		cache = frappe.cache()
		key = locks.session_key("heartbeat-restore-test")
		token = locks.acquire(key, 30)
		self.assertTrue(token)
		beat = locks.Heartbeat(every=0.5)
		beat.watch(key, token, 30)
		try:
			cache.delete(cache.make_key(key))
			self.assertFalse(locks.held(key))
			time.sleep(1.5)
			self.assertTrue(locks.held(key))
			self.assertEqual(cache.get(cache.make_key(key)).decode(), token)
			self.assertGreaterEqual(beat.restored, 1)
		finally:
			beat.stop()
			locks.release(key, token)

	def test_another_turn_s_lock_is_left_alone(self):
		cache = frappe.cache()
		key = locks.session_key("heartbeat-foreign-test")
		token = locks.acquire(key, 30)
		beat = locks.Heartbeat(every=0.5)
		beat.watch(key, token, 30)
		try:
			cache.set(cache.make_key(key), "another-turn", ex=30)
			time.sleep(1.5)
			self.assertEqual(cache.get(cache.make_key(key)).decode(), "another-turn")
			self.assertEqual(beat.restored, 0)
		finally:
			beat.stop()
			cache.delete(cache.make_key(key))
