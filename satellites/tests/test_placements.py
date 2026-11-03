from django.test import SimpleTestCase

from satellites.services import placements as rules

from .fixtures import CATALOGUE, FRAME_1U, FRAME_3U, placements


class SchemaTests(SimpleTestCase):
    def test_valid_document_is_normalized(self):
        doc = placements([("obc", 0)], [("body-3u", "+X")])
        clean, errors = rules.check_schema(doc, CATALOGUE)
        self.assertEqual(errors, [])
        self.assertEqual(clean, doc)

    def test_missing_lists_default_to_empty(self):
        clean, errors = rules.check_schema({}, CATALOGUE)
        self.assertEqual(errors, [])
        self.assertEqual(clean, {"internal": [], "faces": []})

    def assertSchemaError(self, doc, fragment):
        clean, errors = rules.check_schema(doc, CATALOGUE)
        self.assertIsNone(clean)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_rejects_non_object(self):
        self.assertSchemaError([], "object")

    def test_rejects_non_list_sections(self):
        self.assertSchemaError({"internal": "x"}, "internal")
        self.assertSchemaError({"faces": 3}, "faces")

    def test_rejects_unknown_keys(self):
        self.assertSchemaError({"internal": [], "extra": []}, "extra")

    def test_rejects_unknown_module(self):
        self.assertSchemaError(placements([("nope", 0)]), "nope")

    def test_rejects_unhashable_module_value(self):
        self.assertSchemaError({"internal": [{"module": ["obc"], "start_slot": 0}]}, "ไม่พบโมดูล")

    def test_rejects_bad_start_slot(self):
        for value in (-1, 1.5, "2", True, None):
            self.assertSchemaError({"internal": [{"module": "obc", "start_slot": value}]}, "start_slot")

    def test_rejects_bad_face(self):
        for value in ("+W", 1, None, ["+X"]):
            self.assertSchemaError({"faces": [{"module": "body-3u", "face": value}]}, "face")

    def test_rejects_wrong_mount_section(self):
        self.assertSchemaError(placements([("body-3u", 0)]), "ไม่ใช่โมดูลภายใน")
        self.assertSchemaError(placements(faces=[("obc", "+X")]), "ติดที่ผิวโครงไม่ได้")


class AllowedFacesTests(SimpleTestCase):
    def test_full_length_panel_on_long_faces_only(self):
        self.assertEqual(rules.allowed_faces(CATALOGUE["body-3u"], 3), ["+X", "-X", "+Y", "-Y"])

    def test_end_size_panel_on_end_faces_of_long_frames(self):
        self.assertEqual(rules.allowed_faces(CATALOGUE["body-1u"], 3), ["+Z", "-Z"])

    def test_end_size_panel_on_any_face_of_a_1u(self):
        self.assertEqual(len(rules.allowed_faces(CATALOGUE["body-1u"], 1)), 6)

    def test_deployable_never_on_end_faces(self):
        self.assertEqual(rules.allowed_faces(CATALOGUE["deploy-3u"], 3), ["+X", "-X", "+Y", "-Y"])

    def test_no_faces_when_frame_does_not_fit(self):
        self.assertEqual(rules.allowed_faces(CATALOGUE["deploy-3u"], 1), [])

    def test_internal_modules_have_no_faces(self):
        self.assertEqual(rules.allowed_faces(CATALOGUE["obc"], 3), [])


class LayoutTests(SimpleTestCase):
    def test_valid_layout(self):
        doc = placements([("obc", 0)], [("body-3u", "+X"), ("deploy-3u", "-X"), ("body-1u", "+Z")])
        self.assertEqual(rules.check_layout(FRAME_3U, doc, CATALOGUE), [])

    def test_duplicate_face(self):
        doc = placements(faces=[("body-3u", "+X"), ("deploy-3u", "+X")])
        errors = rules.check_layout(FRAME_3U, doc, CATALOGUE)
        self.assertEqual(len(errors), 1)
        self.assertIn("หนึ่งด้านติดได้หนึ่งแผง", errors[0])

    def test_panel_for_another_frame_size(self):
        errors = rules.check_layout(FRAME_1U, placements(faces=[("body-3u", "+X")]), CATALOGUE)
        self.assertIn("ใช้กับโครง 1U ไม่ได้", errors[0])

    def test_wrong_face_for_panel(self):
        errors = rules.check_layout(FRAME_3U, placements(faces=[("body-3u", "+Z")]), CATALOGUE)
        self.assertIn("+Z", errors[0])
