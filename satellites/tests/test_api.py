import io
import json

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase

from satellites.models import Design, Frame, Module

User = get_user_model()
PASSWORD = "orbit-Trajectory-42"

VALID_PLACEMENTS = {
    "internal": [
        {"module": "obc-basic", "start_slot": 0},
        {"module": "battery-40wh", "start_slot": 1},
    ],
    "faces": [{"module": "solar-body-3u", "face": "+X"}],
}


class ApiTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_data", stdout=io.StringIO())
        cls.frame_3u = Frame.objects.get(size_u=3)
        cls.frame_1u = Frame.objects.get(size_u=1)
        cls.alice = User.objects.create_user("alice", password=PASSWORD)
        cls.bob = User.objects.create_user("bob", password=PASSWORD)

    def post(self, url, payload):
        return self.client.post(url, json.dumps(payload), content_type="application/json")

    def put(self, url, payload):
        return self.client.put(url, json.dumps(payload), content_type="application/json")

    def design_payload(self, **overrides):
        return {
            "name": "My Sat",
            "frame": self.frame_3u.id,
            "mission_type": "SCIENCE",
            "altitude_km": 500,
            "placements": VALID_PLACEMENTS,
            **overrides,
        }

    def make_design(self, owner=None, **overrides):
        fields = {
            "owner": owner or self.alice,
            "name": "Saved",
            "frame": self.frame_3u,
            "mission_type": "SCIENCE",
            "altitude_km": 500,
            "placements": VALID_PLACEMENTS,
            **overrides,
        }
        return Design.objects.create(**fields)


class CsrfTests(ApiTestCase):
    def test_csrf_endpoint_sets_cookie(self):
        response = self.client.get("/api/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)

    def test_post_without_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post("/api/evaluate/", "{}", content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_post_with_token_is_accepted(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/api/csrf/")
        token = client.cookies["csrftoken"].value
        response = client.post(
            "/api/evaluate/",
            json.dumps({"frame": self.frame_3u.id, "mission_type": "SCIENCE"}),
            content_type="application/json",
            headers={"X-CSRFToken": token},
        )
        self.assertEqual(response.status_code, 200)


class AuthTests(ApiTestCase):
    def test_register_logs_the_user_in(self):
        response = self.post("/api/auth/register/", {"username": "carol", "password": PASSWORD})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.get("/api/auth/me/").json()["user"]["username"], "carol")

    def test_register_rejects_duplicate_username(self):
        response = self.post("/api/auth/register/", {"username": "alice", "password": PASSWORD})
        self.assertEqual(response.status_code, 400)

    def test_register_rejects_weak_password(self):
        response = self.post("/api/auth/register/", {"username": "carol", "password": "123"})
        self.assertEqual(response.status_code, 400)
        details = response.json()["details"]
        self.assertIn("รหัสผ่านสั้นเกินไป ต้องมีอย่างน้อย 8 ตัวอักษร", details)
        self.assertIn("รหัสผ่านต้องไม่เป็นตัวเลขทั้งหมด", details)

    def test_register_rejects_bad_username_and_email_in_thai(self):
        response = self.post("/api/auth/register/", {"username": "no spaces!", "password": PASSWORD, "email": "nope"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()["details"]), {"ชื่อผู้ใช้หรืออีเมลมีรูปแบบไม่ถูกต้อง"})

    def test_register_rejects_missing_fields(self):
        self.assertEqual(self.post("/api/auth/register/", {"password": PASSWORD}).status_code, 400)
        self.assertEqual(self.post("/api/auth/register/", {"username": "carol"}).status_code, 400)

    def test_login_and_logout(self):
        response = self.post("/api/auth/login/", {"username": "alice", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me/").json()["user"]["username"], "alice")
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 200)
        self.assertIsNone(self.client.get("/api/auth/me/").json()["user"])

    def test_login_with_wrong_password(self):
        response = self.post("/api/auth/login/", {"username": "alice", "password": "wrong"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())

    def test_demo_account_cannot_log_in(self):
        response = self.post("/api/auth/login/", {"username": "demo", "password": ""})
        self.assertEqual(response.status_code, 401)

    def test_method_not_allowed(self):
        self.assertEqual(self.client.get("/api/auth/login/").status_code, 405)


class CatalogueTests(ApiTestCase):
    def test_frames(self):
        data = self.client.get("/api/frames/").json()["frames"]
        self.assertEqual([frame["size_u"] for frame in data], [1, 3, 6])

    def test_modules_are_json_numbers(self):
        data = self.client.get("/api/modules/").json()["modules"]
        self.assertGreaterEqual(len(data), 18)
        self.assertIsInstance(data[0]["price_usd"], float)
        self.assertIn("3", data[0]["allowed_faces"])

    def test_filter_by_category(self):
        data = self.client.get("/api/modules/?category=COMMS").json()["modules"]
        self.assertTrue(data)
        self.assertEqual({module["category"] for module in data}, {"COMMS"})

    def test_filter_by_frame_size_keeps_universal_modules(self):
        slugs = {module["slug"] for module in self.client.get("/api/modules/?frame_size=1").json()["modules"]}
        self.assertIn("obc-basic", slugs)
        self.assertIn("solar-body-1u", slugs)
        self.assertNotIn("solar-body-3u", slugs)
        self.assertNotIn("solar-deploy-3u", slugs)

    def test_bad_filters(self):
        self.assertEqual(self.client.get("/api/modules/?category=NOPE").status_code, 400)
        self.assertEqual(self.client.get("/api/modules/?frame_size=abc").status_code, 400)


class EvaluateTests(ApiTestCase):
    def payload(self, **overrides):
        return {
            "frame": self.frame_3u.id,
            "mission_type": "SCIENCE",
            "altitude_km": 500,
            "placements": VALID_PLACEMENTS,
            **overrides,
        }

    def test_anonymous_can_evaluate(self):
        response = self.post("/api/evaluate/", self.payload())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["mass"]["total_g"], 450 + 70 + 260 + 140)
        self.assertEqual(data["slots"]["occupied"], [0, 1])
        self.assertEqual(data["orbit"]["period_min"], 94.5)
        self.assertEqual(data["cost_usd"], 12300.0)

    def test_overlap_is_reported_in_the_result_not_as_a_400(self):
        placements = {
            "internal": [
                {"module": "battery-80wh", "start_slot": 0},
                {"module": "obc-basic", "start_slot": 1},
            ],
        }
        response = self.post("/api/evaluate/", self.payload(placements=placements))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["slots"]["conflicts"], [1])
        self.assertTrue(response.json()["errors"])

    def test_malformed_placements(self):
        response = self.post("/api/evaluate/", self.payload(placements={"internal": [{"module": "nope"}]}))
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json()["details"])

    def test_bad_inputs(self):
        for bad in ({"frame": 99999}, {"frame": "x"}, {"mission_type": "PARTY"}, {"altitude_km": 100},
                    {"altitude_km": 900}, {"altitude_km": "500"}, {"altitude_km": True}):
            response = self.post("/api/evaluate/", self.payload(**bad))
            self.assertEqual(response.status_code, 400, bad)

    def test_invalid_json(self):
        response = self.client.post("/api/evaluate/", "{not json", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_non_object_json(self):
        response = self.client.post("/api/evaluate/", "[1]", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get("/api/evaluate/").status_code, 405)


class SimulateTests(ApiTestCase):
    def test_returns_series(self):
        response = self.post("/api/simulate/", {"altitude_km": 500, "placements": VALID_PLACEMENTS})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data["series"]), 1000)
        self.assertEqual(set(data["series"][0]), {"t_min", "battery_pct", "in_eclipse"})
        self.assertIn(data["status"], ("OK", "WARNING", "FAILED"))

    def test_no_battery_fails(self):
        response = self.post("/api/simulate/", {"placements": {"internal": [{"module": "obc-basic", "start_slot": 0}]}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "FAILED")

    def test_bad_altitude(self):
        self.assertEqual(self.post("/api/simulate/", {"altitude_km": 10}).status_code, 400)


class DesignCrudTests(ApiTestCase):
    def test_requires_login(self):
        self.assertEqual(self.client.get("/api/designs/").status_code, 401)
        self.assertEqual(self.post("/api/designs/", self.design_payload()).status_code, 401)
        design = self.make_design()
        self.assertEqual(self.client.get(f"/api/designs/{design.id}/").status_code, 401)

    def test_create_sets_owner_and_share_slug(self):
        self.client.force_login(self.alice)
        response = self.post("/api/designs/", self.design_payload())
        self.assertEqual(response.status_code, 201)
        data = response.json()["design"]
        self.assertEqual(data["owner"], "alice")
        self.assertTrue(data["share_slug"])
        self.assertFalse(data["is_public"])
        self.assertEqual(data["frame"]["id"], self.frame_3u.id)

    def test_share_slugs_are_unique(self):
        self.assertNotEqual(self.make_design().share_slug, self.make_design().share_slug)

    def test_create_rejects_missing_or_invalid_fields(self):
        self.client.force_login(self.alice)
        no_frame = self.design_payload()
        del no_frame["frame"]
        no_mission = self.design_payload()
        del no_mission["mission_type"]
        for payload in (no_frame, no_mission, self.design_payload(name="  "), self.design_payload(name="x" * 101),
                        self.design_payload(altitude_km=50), self.design_payload(is_public="yes"),
                        self.design_payload(placements="nope")):
            self.assertEqual(self.post("/api/designs/", payload).status_code, 400, payload)
        self.assertEqual(Design.objects.filter(owner=self.alice).count(), 0)

    def test_create_rejects_overlapping_slots(self):
        self.client.force_login(self.alice)
        placements = {
            "internal": [
                {"module": "battery-80wh", "start_slot": 0},
                {"module": "obc-basic", "start_slot": 1},
            ],
        }
        response = self.post("/api/designs/", self.design_payload(placements=placements))
        self.assertEqual(response.status_code, 400)
        self.assertTrue(any("ซ้อนทับ" in detail for detail in response.json()["details"]))

    def test_create_rejects_two_panels_on_one_face(self):
        self.client.force_login(self.alice)
        placements = {
            "faces": [
                {"module": "solar-body-3u", "face": "+X"},
                {"module": "solar-deploy-3u", "face": "+X"},
            ],
        }
        self.assertEqual(self.post("/api/designs/", self.design_payload(placements=placements)).status_code, 400)

    def test_create_rejects_panel_for_wrong_frame(self):
        self.client.force_login(self.alice)
        placements = {"faces": [{"module": "solar-body-3u", "face": "+X"}]}
        payload = self.design_payload(frame=self.frame_1u.id, placements=placements)
        self.assertEqual(self.post("/api/designs/", payload).status_code, 400)

    def test_over_mass_design_can_still_be_saved(self):
        Module.objects.create(name="Anvil", slug="anvil", category="PAYLOAD", mount_type="INTERNAL",
                              slots=1, mass_g=9000)
        self.client.force_login(self.alice)
        heavy = {"internal": [{"module": "anvil", "start_slot": 0}]}
        response = self.post("/api/designs/", self.design_payload(placements=heavy))
        self.assertEqual(response.status_code, 201)

    def test_slots_past_the_end_of_the_frame_cannot_be_saved(self):
        self.client.force_login(self.alice)
        placements = {
            "internal": [
                {"module": "camera-hd", "start_slot": 0},
                {"module": "reaction-wheels", "start_slot": 4},
            ],
        }
        response = self.post("/api/designs/", self.design_payload(frame=self.frame_1u.id, placements=placements))
        self.assertEqual(response.status_code, 400)

    def test_list_returns_only_my_designs_with_summary(self):
        mine = self.make_design()
        self.make_design(owner=self.bob, name="Bob's")
        self.client.force_login(self.alice)
        data = self.client.get("/api/designs/").json()["designs"]
        self.assertEqual([design["id"] for design in data], [mine.id])
        self.assertEqual(data[0]["summary"]["module_count"], 3)

    def test_update(self):
        design = self.make_design()
        self.client.force_login(self.alice)
        response = self.put(f"/api/designs/{design.id}/", {"name": "Renamed", "is_public": True})
        self.assertEqual(response.status_code, 200)
        design.refresh_from_db()
        self.assertEqual(design.name, "Renamed")
        self.assertTrue(design.is_public)
        self.assertEqual(design.altitude_km, 500)

    def test_update_validates(self):
        design = self.make_design()
        self.client.force_login(self.alice)
        self.assertEqual(self.put(f"/api/designs/{design.id}/", {"altitude_km": 9000}).status_code, 400)
        design.refresh_from_db()
        self.assertEqual(design.altitude_km, 500)

    def test_update_to_smaller_frame_revalidates_saved_placements(self):
        design = self.make_design()
        self.client.force_login(self.alice)
        response = self.put(f"/api/designs/{design.id}/", {"frame": self.frame_1u.id})
        self.assertEqual(response.status_code, 400)

    def test_delete(self):
        design = self.make_design()
        self.client.force_login(self.alice)
        self.assertEqual(self.client.delete(f"/api/designs/{design.id}/").status_code, 200)
        self.assertFalse(Design.objects.filter(pk=design.id).exists())

    def test_other_users_get_403(self):
        design = self.make_design()
        self.client.force_login(self.bob)
        url = f"/api/designs/{design.id}/"
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.put(url, {"name": "Stolen"}).status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)
        design.refresh_from_db()
        self.assertEqual(design.name, "Saved")

    def test_missing_design_gets_404_json(self):
        self.client.force_login(self.alice)
        response = self.client.get("/api/designs/999999/")
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())


class SharingTests(ApiTestCase):
    def test_gallery_lists_only_public_designs(self):
        self.make_design(name="Secret")
        public = self.make_design(name="Open", is_public=True)
        data = self.client.get("/api/gallery/").json()["designs"]
        names = [design["name"] for design in data]
        self.assertIn(public.name, names)
        self.assertNotIn("Secret", names)
        self.assertEqual(len(names), 4)  # three seeded + one public

    def test_gallery_summary_flags_the_failed_demo(self):
        data = self.client.get("/api/gallery/").json()["designs"]
        statuses = {design["name"]: design["summary"]["battery_status"] for design in data}
        self.assertEqual(statuses["Blackout-3U (ตัวอย่างแบบที่ล้มเหลว)"], "FAILED")

    def test_gallery_survives_a_module_removed_from_the_catalogue(self):
        self.make_design(is_public=True, placements={"internal": [{"module": "gone", "start_slot": 0}], "faces": []})
        self.assertEqual(self.client.get("/api/gallery/").status_code, 200)

    def test_share_link_works_anonymously_even_when_private(self):
        design = self.make_design(name="Unlisted")
        response = self.client.get(f"/api/shared/{design.share_slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["design"]["name"], "Unlisted")

    def test_unknown_share_link(self):
        self.assertEqual(self.client.get("/api/shared/not-a-real-slug/").status_code, 404)
