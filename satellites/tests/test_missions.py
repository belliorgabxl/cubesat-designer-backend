from django.test import SimpleTestCase

from satellites.services import missions

from .fixtures import CATALOGUE


def build(*slugs):
    return [CATALOGUE[slug] for slug in slugs]


class MissionTests(SimpleTestCase):
    def test_complete_earth_observation(self):
        modules = build("camera-small", "wheels", "uhf", "battery", "obc")
        self.assertEqual(missions.check_mission("EARTH_OBSERVATION", modules)["missing"], [])

    def test_empty_earth_observation_lists_all_five_in_thai(self):
        result = missions.check_mission("EARTH_OBSERVATION", [])
        self.assertEqual(result["type"], "EARTH_OBSERVATION")
        self.assertEqual(len(result["missing"]), 5)
        self.assertTrue(all("ต้องมี" in message for message in result["missing"]))

    def test_earth_observation_payload_must_be_a_camera(self):
        modules = build("sensor", "wheels", "uhf", "battery", "obc")
        missing = missions.check_mission("EARTH_OBSERVATION", modules)["missing"]
        self.assertEqual(len(missing), 1)
        self.assertIn("กล้อง", missing[0])

    def test_communication_needs_no_payload(self):
        self.assertEqual(missions.check_mission("COMMUNICATION", build("uhf", "battery", "obc"))["missing"], [])

    def test_communication_missing_comms(self):
        missing = missions.check_mission("COMMUNICATION", build("battery", "obc"))["missing"]
        self.assertEqual(len(missing), 1)
        self.assertIn("COMMS", missing[0])

    def test_science_accepts_any_payload(self):
        self.assertEqual(missions.check_mission("SCIENCE", build("sensor", "battery", "obc"))["missing"], [])
        self.assertEqual(missions.check_mission("SCIENCE", build("camera-small", "battery", "obc"))["missing"], [])

    def test_science_missing_battery(self):
        missing = missions.check_mission("SCIENCE", build("sensor", "obc"))["missing"]
        self.assertEqual(len(missing), 1)
        self.assertIn("แบตเตอรี่", missing[0])
