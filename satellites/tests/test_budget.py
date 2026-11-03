from django.test import SimpleTestCase

from satellites.services import budget

from .fixtures import CATALOGUE, FRAME_1U, FRAME_3U, module


class MassBudgetTests(SimpleTestCase):
    def test_sums_frame_and_modules(self):
        result = budget.mass_budget(FRAME_3U, [module("a", mass_g=1000), module("b", mass_g=550)])
        self.assertEqual(result, {"total_g": 2000, "max_g": 6000, "pct": 33.3, "status": "OK"})

    def test_exactly_90_percent_is_still_ok(self):
        self.assertEqual(budget.mass_budget(FRAME_1U, [module("a", mass_g=1620)])["status"], "OK")

    def test_warning_above_90_percent(self):
        self.assertEqual(budget.mass_budget(FRAME_1U, [module("a", mass_g=1621)])["status"], "WARNING")

    def test_exactly_at_limit_is_warning_not_error(self):
        self.assertEqual(budget.mass_budget(FRAME_1U, [module("a", mass_g=1820)])["status"], "WARNING")

    def test_error_above_limit(self):
        self.assertEqual(budget.mass_budget(FRAME_1U, [module("a", mass_g=1821)])["status"], "ERROR")


class SlotBudgetTests(SimpleTestCase):
    def test_reports_used_and_free_slots(self):
        internal = [{"module": "obc", "start_slot": 0}, {"module": "wheels", "start_slot": 2}]
        result = budget.slot_budget(FRAME_1U, internal, CATALOGUE)
        self.assertEqual(result["used"], 3)
        self.assertEqual(result["total"], 4)
        self.assertEqual(result["occupied"], [0, 2, 3])
        self.assertEqual(result["free"], [1])
        self.assertEqual(result["conflicts"], [])
        self.assertEqual(result["out_of_range"], [])

    def test_detects_overlap(self):
        internal = [{"module": "wheels", "start_slot": 0}, {"module": "obc", "start_slot": 1}]
        result = budget.slot_budget(FRAME_3U, internal, CATALOGUE)
        self.assertEqual(result["conflicts"], [1])
        self.assertEqual(result["used"], 2)

    def test_detects_module_past_the_end_of_the_frame(self):
        result = budget.slot_budget(FRAME_1U, [{"module": "wheels", "start_slot": 3}], CATALOGUE)
        self.assertEqual(result["out_of_range"], [4])
        self.assertEqual(result["occupied"], [3])


class PowerBudgetTests(SimpleTestCase):
    def test_orientation_factors_by_panel_type(self):
        panels = [CATALOGUE["body-3u"], CATALOGUE["deploy-3u"]]
        self.assertAlmostEqual(budget.sunlit_generation_w(panels), 7 * 0.5 + 14 * 0.75)

    def test_factors_can_be_overridden(self):
        panels = [CATALOGUE["body-3u"]]
        self.assertAlmostEqual(budget.sunlit_generation_w(panels, {"SOLAR_BODY": 1.0}), 7.0)

    def test_average_accounts_for_eclipse(self):
        result = budget.power_budget([CATALOGUE["deploy-3u"], CATALOGUE["obc"]], eclipse_fraction=0.4)
        self.assertEqual(result["generate_sunlit_w"], 10.5)
        self.assertEqual(result["generate_avg_w"], 6.3)
        self.assertEqual(result["consume_w"], 0.4)
        self.assertEqual(result["status"], "OK")

    def test_warns_when_average_generation_is_below_consumption(self):
        result = budget.power_budget([CATALOGUE["body-1u"], CATALOGUE["wheels"]], eclipse_fraction=0.4)
        self.assertEqual(result["status"], "WARNING")

    def test_no_modules(self):
        result = budget.power_budget([], eclipse_fraction=0.4)
        self.assertEqual(result, {"generate_sunlit_w": 0, "generate_avg_w": 0, "consume_w": 0, "status": "OK"})


class CostTests(SimpleTestCase):
    def test_sums_prices(self):
        self.assertEqual(budget.total_cost_usd([module("a", price=10.5), module("b", price=20)]), 30.5)
