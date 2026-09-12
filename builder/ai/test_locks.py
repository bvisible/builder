import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai import locks


class TestLocks(FrappeTestCase):
	def setUp(self):
		self.key = f"builder_ai_test_lock:{frappe.generate_hash(length=8)}"

	def tearDown(self):
		cache = frappe.cache()
		cache.delete_value(cache.make_key(self.key))

	def test_acquiring_returns_a_token(self):
		self.assertTrue(locks.acquire(self.key, 30))

	def test_a_held_lock_cannot_be_acquired_again(self):
		locks.acquire(self.key, 30)

		self.assertIsNone(locks.acquire(self.key, 30))

	def test_releasing_frees_the_lock(self):
		token = locks.acquire(self.key, 30)
		locks.release(self.key, token)

		self.assertTrue(locks.acquire(self.key, 30))

	def test_a_stale_token_cannot_release_a_newer_holder(self):
		stale = locks.acquire(self.key, 30)
		locks.release(self.key, stale)
		current = locks.acquire(self.key, 30)

		locks.release(self.key, stale)

		self.assertIsNone(locks.acquire(self.key, 30))
		locks.release(self.key, current)

	def test_releasing_without_a_token_does_nothing(self):
		token = locks.acquire(self.key, 30)
		locks.release(self.key, None)

		self.assertIsNone(locks.acquire(self.key, 30))
		locks.release(self.key, token)

	def test_held_reports_the_lock(self):
		self.assertFalse(locks.held(self.key))
		token = locks.acquire(self.key, 30)

		self.assertTrue(locks.held(self.key))
		locks.release(self.key, token)
		self.assertFalse(locks.held(self.key))

	def test_guard_releases_on_the_way_out(self):
		with locks.guard(self.key, 30) as token:
			self.assertTrue(token)
			self.assertTrue(locks.held(self.key))

		self.assertFalse(locks.held(self.key))

	def test_guard_yields_nothing_when_the_lock_is_taken(self):
		token = locks.acquire(self.key, 30)

		with locks.guard(self.key, 30) as second:
			self.assertIsNone(second)

		self.assertTrue(locks.held(self.key))
		locks.release(self.key, token)

	def test_keys_are_scoped_per_page_task_and_session(self):
		self.assertNotEqual(locks.page_key("p1"), locks.session_key("p1"))
		self.assertNotEqual(locks.page_key("p1"), locks.page_key("p2"))

	# //// Neoffice — added tests. frappe.clear_cache() erases every key of the site except the
	# //// persistent_cache_keys patterns (builder_ai_* in hooks.py), and the heartbeat is what
	# //// lets a 20-minute site build keep upstream's 11-minute locks.
	def test_a_lock_survives_a_global_cache_clear(self):
		token = locks.acquire(self.key, 30)
		frappe.clear_cache()

		self.assertTrue(locks.held(self.key))
		locks.release(self.key, token)

	def test_the_heartbeat_renews_a_held_lock(self):
		import time

		token = locks.acquire(self.key, 30)
		cache = frappe.cache()
		cache.expire(cache.make_key(self.key), 3)
		beat = locks.Heartbeat(every=0.2)
		beat.watch(self.key, token, 30)
		time.sleep(0.6)
		beat.stop()

		self.assertGreater(cache.ttl(cache.make_key(self.key)), 3)
		locks.release(self.key, token)

	def test_the_heartbeat_never_revives_a_lock_it_no_longer_owns(self):
		import time

		token = locks.acquire(self.key, 30)
		beat = locks.Heartbeat(every=0.2)
		beat.watch(self.key, token, 30)
		locks.release(self.key, token)
		time.sleep(0.5)
		beat.stop()

		self.assertFalse(locks.held(self.key))

	# //// Neoffice — a released token is never restored, even once another turn has come and gone
	# //// under the same key; a lock deleted under a live turn still comes back (#371).
	def test_a_released_token_is_never_restored_after_the_next_turn(self):
		import time

		first = locks.acquire(self.key, 30)
		beat = locks.Heartbeat(every=0.2)
		beat.watch(self.key, first, 30)
		locks.release(self.key, first)
		second = locks.acquire(self.key, 30)
		locks.release(self.key, second)
		time.sleep(0.5)
		beat.stop()

		self.assertFalse(locks.held(self.key))
		self.assertEqual(beat.restored, 0)

	def test_a_lock_deleted_under_a_live_turn_still_comes_back(self):
		import time

		token = locks.acquire(self.key, 30)
		beat = locks.Heartbeat(every=0.2)
		beat.watch(self.key, token, 30)
		cache = frappe.cache()
		cache.delete(cache.make_key(self.key))
		time.sleep(0.5)
		beat.stop()

		self.assertTrue(locks.held(self.key))
		self.assertGreaterEqual(beat.restored, 1)
		locks.release(self.key, token)
