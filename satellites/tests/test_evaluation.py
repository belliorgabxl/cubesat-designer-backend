from django.test import SimpleTestCase

from satellites.services import evaluation

from .fixtures import CATALOGUE, FRAME_1U, FRAME_3U, module, placements

COMPLETE = placements(
    [("obc", 0), ("battery", 1), ("uhf", 2), ("wheels", 3), ("camera-small", 5)],
    [("deploy-3u", "+X")],
)


def evaluate(doc, frame=FRAME_3U, mission="EARTH_OBSERVATION", altitude=500, catalogue=CATALOGUE):
    return evaluation.evaluate_design(frame, doc, catalogue, mission, altitude)


class EvaluateDesignTests(SimpleTestCase):
    def test_result_shape_for_a_healthy_design(self):
        result = evaluate(COMPLETE)
        self.assertEqual(
            set(result),
            {"mass", "slots", "power", "orbit", "mission", "cost_usd", "warnings", "errors"},
        )
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["mass"]["status"], "OK")
        self.assertEqual(result["slots"]["used"], 7)
        self.assertEqual(result["orbit"]["altitude_km"], 500)
        self.assertEqual(result["mission"]["missing"], [])
        self.assertEqual(result["cost_usd"], 600.0)

    def test_mission_gaps_become_warnings(self):
        result = evaluate(placements([("obc", 0)]))
        self.assertEqual(len(result["mission"]["missing"]), 4)
        for message in result["mission"]["missing"]:
            self.assertIn(message, result["warnings"])

    def test_power_shortfall_warns(self):
        result = evaluate(placements([("obc", 0), ("battery", 1)]), mission="SCIENCE")
        self.assertEqual(result["power"]["status"], "WARNING")
        self.assertTrue(any("กำลังผลิต" in warning for warning in result["warnings"]))

    def test_overlap_is_an_error(self):
        result = evaluate(placements([("wheels", 0), ("obc", 1)]))
        self.assertEqual(result["slots"]["conflicts"], [1])
        self.assertTrue(any("ซ้อนทับ" in error for error in result["errors"]))

    def test_overflow_is_an_error(self):
        result = evaluate(placements([("wheels", 3)]), frame=FRAME_1U)
        self.assertTrue(any("ล้นโครง" in error for error in result["errors"]))

    def test_overweight_is_an_error(self):
        catalogue = {**CATALOGUE, "anvil": module("anvil", mass_g=9000)}
        result = evaluate(placements([("anvil", 0)]), catalogue=catalogue)
        self.assertEqual(result["mass"]["status"], "ERROR")
        self.assertTrue(any("เกินขีดจำกัด" in error for error in result["errors"]))

    def test_near_limit_mass_warns(self):
        catalogue = {**CATALOGUE, "heavy": module("heavy", mass_g=5300)}
        result = evaluate(placements([("heavy", 0)]), catalogue=catalogue)
        self.assertEqual(result["mass"]["status"], "WARNING")
        self.assertTrue(any("90%" in warning for warning in result["warnings"]))


class SimulateDesignTests(SimpleTestCase):
    def test_uses_placed_modules(self):
        result = evaluation.simulate_design(COMPLETE, CATALOGUE, 500)
        self.assertEqual(result["capacity_wh"], 40.0)
        self.assertEqual(result["generate_sunlit_w"], 10.5)
        self.assertEqual(result["consume_w"], 5.0)
        self.assertEqual(result["status"], "OK")

    def test_without_battery_fails(self):
        result = evaluation.simulate_design(placements([("obc", 0)]), CATALOGUE, 500)
        self.assertEqual(result["status"], "FAILED")


class DesignSummaryTests(SimpleTestCase):
    def test_summary(self):
        result = evaluation.design_summary(FRAME_3U, COMPLETE, CATALOGUE, 500)
        self.assertEqual(result["module_count"], 6)
        self.assertEqual(result["battery_status"], "OK")

    def test_skips_modules_removed_from_the_catalogue(self):
        doc = placements([("obc", 0), ("retired", 1)], [("retired-panel", "+X")])
        self.assertEqual(evaluation.design_summary(FRAME_3U, doc, CATALOGUE, 500)["module_count"], 1)
