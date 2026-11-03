import io

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from satellites.models import Design, Frame, Module
from satellites.serializers import frame_to_dict, module_to_dict
from satellites.services import evaluation


class SeedDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_data", verbosity=0, stdout=io.StringIO())
        cls.catalogue = {module.slug: module_to_dict(module) for module in Module.objects.all()}

    def simulate(self, design):
        return evaluation.simulate_design(design.placements, self.catalogue, design.altitude_km,
                                          settings.SOLAR_ORIENTATION_FACTORS)

    def test_counts(self):
        self.assertEqual(Frame.objects.count(), 3)
        self.assertGreaterEqual(Module.objects.count(), 18)
        self.assertEqual(Design.objects.filter(is_public=True).count(), 3)

    def test_every_category_is_covered(self):
        categories = set(Module.objects.values_list("category", flat=True))
        self.assertEqual(categories, set(Module.Category.values))

    def test_is_idempotent(self):
        call_command("seed_data", verbosity=0, stdout=io.StringIO())
        self.assertEqual(Frame.objects.count(), 3)
        self.assertEqual(Design.objects.count(), 3)

    def test_demo_user_cannot_log_in(self):
        self.assertFalse(get_user_model().objects.get(username="demo").has_usable_password())

    def test_all_demo_layouts_are_valid(self):
        for design in Design.objects.all():
            result = evaluation.evaluate_design(
                frame_to_dict(design.frame), design.placements, self.catalogue,
                design.mission_type, design.altitude_km, settings.SOLAR_ORIENTATION_FACTORS,
            )
            self.assertEqual(result["errors"], [], design.name)
            self.assertEqual(result["mission"]["missing"], [], design.name)

    def test_demo_outcomes(self):
        statuses = {design.name: self.simulate(design)["status"] for design in Design.objects.all()}
        self.assertEqual(statuses["Siam-EO 3U (ถ่ายภาพโลก)"], "OK")
        self.assertEqual(statuses["Relay-1 1U (สื่อสาร)"], "OK")
        self.assertEqual(statuses["Blackout-3U (ตัวอย่างแบบที่ล้มเหลว)"], "FAILED")
