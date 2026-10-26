# //// Neoffice — added file (no upstream equivalent): where the map of a site draws its marker (osm_map.py).
"""The map is OpenStreetMap's embed, which is given a point and not an address. What is pinned here: the addresses asked, most exact first; a
lookup that fails is a miss and never an exception; the answer is cached for a month and a miss for a day, so a visitor never waits twice;
a page that is built carries the point of its map beside the include, once, and keeps a point it already has. No network: the lookup and the
cache are replaced."""

import unittest
from unittest.mock import MagicMock, patch

from builder import osm_map


class Response:
	def __init__(self, body, status=200):
		self.body, self.status = body, status

	def raise_for_status(self):
		if self.status >= 400:
			raise RuntimeError(f"HTTP {self.status}")

	def json(self):
		return self.body


class TestWhatIsAsked(unittest.TestCase):
	def test_the_address_as_written_comes_first_then_without_its_street(self):
		self.assertEqual(["Rue 1, 1950 Sion, Switzerland", "1950 Sion, Switzerland"], osm_map.candidates("Rue 1, 1950 Sion, Switzerland"))

	def test_a_long_address_ends_on_its_postcode_and_town(self):
		self.assertEqual(["A, B, C, D", "B, C, D", "C, D"], osm_map.candidates("A, B, C, D"))

	def test_a_short_address_is_asked_once_and_blanks_are_squeezed(self):
		self.assertEqual(["Sion"], osm_map.candidates("  Sion "))
		self.assertEqual(["1950 Sion, Suisse"], osm_map.candidates("1950   Sion, Suisse"))
		self.assertEqual([], osm_map.candidates(""))


class TestTheLookup(unittest.TestCase):
	def test_the_first_answer_is_the_point(self):
		with patch("requests.get", return_value=Response([{"lat": "45.9852", "lon": "7.1177"}])) as get, patch("time.sleep") as sleep:
			self.assertEqual((45.9852, 7.1177), osm_map.look_up("Rue 1, 1950 Sion, Switzerland"))
		self.assertEqual(1, get.call_count)
		sleep.assert_not_called()
		self.assertIn("Neoffice", get.call_args.kwargs["headers"]["User-Agent"])
		self.assertEqual("https://nominatim.openstreetmap.org/search", get.call_args.args[0])

	def test_an_address_it_does_not_know_is_asked_again_without_its_street_after_a_pause(self):
		answers = [Response([]), Response([{"lat": "46.0", "lon": "7.0"}])]
		with patch("requests.get", side_effect=answers) as get, patch("time.sleep") as sleep:
			self.assertEqual((46.0, 7.0), osm_map.look_up("Rue 1, 1950 Sion, Switzerland"))
		self.assertEqual("1950 Sion, Switzerland", get.call_args.kwargs["params"]["q"])
		sleep.assert_called_once_with(osm_map.PAUSE)

	def test_nothing_found_is_a_miss(self):
		with patch("requests.get", return_value=Response([])), patch("time.sleep"):
			self.assertIsNone(osm_map.look_up("Rue 1, 1950 Sion, Switzerland"))

	def test_an_unreachable_service_is_a_miss_never_an_exception(self):
		with patch("requests.get", side_effect=OSError("timeout")):
			self.assertIsNone(osm_map.look_up("Rue 1, Sion"))
		with patch("requests.get", return_value=Response([], status=429)):
			self.assertIsNone(osm_map.look_up("Rue 1, Sion"))


class TestTheCache(unittest.TestCase):
	def cache(self, stored=None):
		cache = MagicMock()
		cache.get_value.return_value = stored
		return cache

	def test_a_found_point_is_kept_for_a_month(self):
		cache = self.cache()
		with patch.object(osm_map.frappe, "cache", cache), patch.object(osm_map, "look_up", return_value=(46.0, 7.0)) as look:
			self.assertEqual([46.0, 7.0], osm_map.geocode_address("Rue 1, Sion"))
		look.assert_called_once()
		self.assertEqual(osm_map.FOUND_FOR, cache.set_value.call_args.kwargs["expires_in_sec"])

	def test_a_kept_point_is_not_looked_up_again(self):
		with patch.object(osm_map.frappe, "cache", self.cache([46.0, 7.0])), patch.object(osm_map, "look_up") as look:
			self.assertEqual([46.0, 7.0], osm_map.geocode_address("Rue 1, Sion"))
		look.assert_not_called()

	def test_a_miss_is_kept_for_a_day_and_answered_as_none(self):
		cache = self.cache()
		with patch.object(osm_map.frappe, "cache", cache), patch.object(osm_map, "look_up", return_value=None):
			self.assertIsNone(osm_map.geocode_address("Nowhere"))
		self.assertEqual(([], osm_map.MISSED_FOR), (cache.set_value.call_args.args[1], cache.set_value.call_args.kwargs["expires_in_sec"]))
		with patch.object(osm_map.frappe, "cache", self.cache([])), patch.object(osm_map, "look_up") as look:
			self.assertIsNone(osm_map.geocode_address("Nowhere"))
		look.assert_not_called()

	def test_a_cache_that_fails_does_not_fail_the_page(self):
		cache = MagicMock()
		cache.get_value.side_effect = RuntimeError("redis is down")
		cache.set_value.side_effect = RuntimeError("redis is down")
		with patch.object(osm_map.frappe, "cache", cache), patch.object(osm_map, "look_up", return_value=(46.0, 7.0)):
			self.assertEqual([46.0, 7.0], osm_map.geocode_address("Rue 1, Sion"))

	def test_an_empty_address_is_not_looked_up(self):
		with patch.object(osm_map, "look_up") as look:
			self.assertIsNone(osm_map.geocode_address("   "))
			self.assertIsNone(osm_map.geocode_address(None))
		look.assert_not_called()

	def test_two_spellings_of_one_address_share_one_key(self):
		self.assertEqual(osm_map._key("Rue 1,  Sion"), osm_map._key(" rue 1, sion"))


def include(*before):
	return "".join(before) + "{% include 'builder/templates/includes/google_map.html' %}"


def holder(html, *children):
	return {"element": "div", "innerHTML": html, "children": list(children)}


class TestAPageCarriesThePointOfItsMap(unittest.TestCase):
	def test_the_point_is_written_beside_the_include(self):
		block = holder(include('{% set address = "Rue 1, 1950 Sion" %}', '{% set height = "400px" %}'))
		with patch.object(osm_map, "geocode_address", return_value=[46.2, 7.35]) as geocode:
			edits = osm_map.pin_maps([block])
		geocode.assert_called_once_with("Rue 1, 1950 Sion")
		self.assertTrue(block["innerHTML"].endswith('{% set lat = "46.200000" %}{% set lon = "7.350000" %}{% include \'builder/templates/includes/google_map.html\' %}'))
		self.assertEqual(1, len(edits))

	def test_a_map_with_no_address_of_its_own_takes_the_business_address(self):
		block = holder(include())
		with patch.object(osm_map, "geocode_address", return_value=[46.2, 7.35]) as geocode:
			osm_map.pin_maps([block], "Rue 2, 1920 Sion")
		geocode.assert_called_once_with("Rue 2, 1920 Sion")
		self.assertIn("set lat", block["innerHTML"])

	def test_a_map_with_no_address_at_all_is_left_alone(self):
		block = holder(include())
		with patch.object(osm_map, "geocode_address") as geocode:
			self.assertEqual([], osm_map.pin_maps([block]))
		geocode.assert_not_called()
		self.assertNotIn("set lat", block["innerHTML"])

	def test_a_point_the_page_already_has_is_kept(self):
		html = include('{% set address = "Rue 1" %}{% set lat = "1.0" %}{% set lon = "2.0" %}')
		block = holder(html)
		with patch.object(osm_map, "geocode_address") as geocode:
			self.assertEqual([], osm_map.pin_maps([block]))
		geocode.assert_not_called()
		self.assertEqual(html, block["innerHTML"])

	def test_a_second_run_changes_nothing(self):
		block = holder(include('{% set address = "Rue 1" %}'))
		with patch.object(osm_map, "geocode_address", return_value=[46.2, 7.35]):
			osm_map.pin_maps([block])
			once = block["innerHTML"]
			osm_map.pin_maps([block])
		self.assertEqual(once, block["innerHTML"])

	def test_an_address_nobody_can_place_is_said_not_invented(self):
		block = holder(include('{% set address = "Nowhere" %}'))
		with patch.object(osm_map, "geocode_address", return_value=None):
			edits = osm_map.pin_maps([block])
		self.assertEqual(["no point found for Nowhere"], edits)
		self.assertNotIn("set lat", block["innerHTML"])

	def test_a_map_deep_in_the_page_is_found_and_other_blocks_are_not_touched(self):
		deep = holder(include('{% set address = "Rue 1" %}'))
		other = holder("{% include 'builder/templates/includes/contact_form.html' %}")
		blocks = [{"element": "div", "children": [{"element": "section", "children": [other, deep]}]}]
		with patch.object(osm_map, "geocode_address", return_value=[46.2, 7.35]):
			osm_map.pin_maps(blocks)
		self.assertIn("set lat", deep["innerHTML"])
		self.assertNotIn("set lat", other["innerHTML"])


if __name__ == "__main__":
	unittest.main()
