from django.test import SimpleTestCase

from satellites.services import orbit


class OrbitTests(SimpleTestCase):
    def test_period_at_500_km(self):
        self.assertAlmostEqual(orbit.orbital_period_s(500) / 60, 94.5, delta=0.2)

    def test_eclipse_fraction_at_500_km(self):
        self.assertAlmostEqual(orbit.eclipse_fraction(500), 0.37, delta=0.01)

    def test_higher_orbit_is_slower_with_less_eclipse(self):
        self.assertGreater(orbit.orbital_period_s(800), orbit.orbital_period_s(300))
        self.assertLess(orbit.eclipse_fraction(800), orbit.eclipse_fraction(300))

    def test_in_eclipse_is_centred_on_half_orbit(self):
        period = 6000.0
        fraction = 0.4
        self.assertFalse(orbit.in_eclipse(0, period, fraction))
        self.assertTrue(orbit.in_eclipse(3000, period, fraction))
        self.assertFalse(orbit.in_eclipse(1700, period, fraction))
        self.assertTrue(orbit.in_eclipse(1900, period, fraction))
        self.assertTrue(orbit.in_eclipse(4100, period, fraction))
        self.assertFalse(orbit.in_eclipse(4300, period, fraction))
        self.assertTrue(orbit.in_eclipse(6000 + 3000, period, fraction))

    def test_summary_is_rounded(self):
        self.assertEqual(orbit.orbit_summary(500), {"altitude_km": 500, "period_min": 94.5, "eclipse_fraction": 0.378})
