from django.test import SimpleTestCase

from satellites.services import orbit, simulation


class SimulationTests(SimpleTestCase):
    def test_no_battery_fails_with_reason(self):
        result = simulation.simulate_battery(0, 10, 2, 500)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["series"], [])
        self.assertEqual(result["min_battery_pct"], 0.0)
        self.assertIn("ไม่มีแบตเตอรี่", result["reason"])

    def test_covers_three_orbits_in_ten_second_steps(self):
        result = simulation.simulate_battery(40, 10, 2, 500)
        series = result["series"]
        self.assertAlmostEqual(series[1]["t_min"] * 60, simulation.STEP_S, places=1)
        self.assertAlmostEqual(series[-1]["t_min"], 3 * orbit.orbital_period_s(500) / 60, delta=0.2)

    def test_starts_full_and_in_sunlight(self):
        first = simulation.simulate_battery(40, 10, 2, 500)["series"][0]
        self.assertEqual(first, {"t_min": 0.0, "battery_pct": 100.0, "in_eclipse": False})

    def test_eclipse_share_matches_orbit_geometry(self):
        series = simulation.simulate_battery(40, 10, 2, 500)["series"]
        share = sum(point["in_eclipse"] for point in series) / len(series)
        self.assertAlmostEqual(share, orbit.eclipse_fraction(500), delta=0.01)

    def test_healthy_design_is_ok_and_never_exceeds_capacity(self):
        result = simulation.simulate_battery(40, 10, 2, 500)
        self.assertEqual(result["status"], "OK")
        self.assertLessEqual(max(point["battery_pct"] for point in result["series"]), 100.0)
        self.assertLess(result["min_battery_pct"], 100.0)

    def test_warning_below_30_percent(self):
        # About 36 minutes of 10 W eclipse drains 6 Wh, then sunlight tops it back up.
        result = simulation.simulate_battery(7.5, 40, 10, 500)
        self.assertEqual(result["status"], "WARNING")
        self.assertGreater(result["min_battery_pct"], 0)
        self.assertLess(result["min_battery_pct"], 30)

    def test_battery_running_flat_fails_and_clamps_at_zero(self):
        result = simulation.simulate_battery(5, 0, 10, 500)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["min_battery_pct"], 0.0)
        self.assertEqual(min(point["battery_pct"] for point in result["series"]), 0.0)
        self.assertIn("หมด", result["reason"])

    def test_no_load_stays_full(self):
        result = simulation.simulate_battery(20, 0, 0, 500)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["min_battery_pct"], 100.0)
