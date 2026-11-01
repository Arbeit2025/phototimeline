import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["PHOTOTIMELINE_DB"] = _tmp.name

import app as app_module  # noqa: E402


class PhotoTimelineTest(unittest.TestCase):
    def setUp(self):
        app_module.init_db()
        self.client = app_module.app.test_client()
        with app_module.app.app_context():
            conn = app_module.get_db()
            conn.execute("DELETE FROM entries")
            conn.commit()

    def test_healthz(self):
        res = self.client.get("/healthz")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "ok")

    def test_index_ok(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("フォト年表メーカー", res.get_data(as_text=True))

    def test_add_visible_delete_gone(self):
        res = self.client.post(
            "/add", data={"date": "2025-04-01", "title": "桜を見た日", "memo": "川沿いを散歩"}
        )
        self.assertEqual(res.status_code, 302)
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("桜を見た日", body)
        self.assertIn("2025年", body)
        with app_module.app.app_context():
            conn = app_module.get_db()
            eid = conn.execute("SELECT id FROM entries").fetchone()["id"]
        res = self.client.post(f"/delete/{eid}")
        self.assertEqual(res.status_code, 302)
        body = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("桜を見た日", body)

    def test_year_grouping_order(self):
        self.client.post("/add", data={"date": "2024-12-31", "title": "大晦日", "memo": ""})
        self.client.post("/add", data={"date": "2026-01-01", "title": "元日", "memo": ""})
        self.client.post("/add", data={"date": "2026-06-15", "title": "梅雨", "memo": ""})
        body = self.client.get("/").get_data(as_text=True)
        # 新しい年（2026）が先、年内は日付順（元日→梅雨）
        self.assertLess(body.index("2026年"), body.index("2024年"))
        self.assertLess(body.index("元日"), body.index("梅雨"))

    def test_invalid_date_rejected(self):
        self.client.post("/add", data={"date": "2025/04/01", "title": "だめな日付", "memo": ""})
        body = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("だめな日付", body)

    def test_delete_missing_redirects(self):
        res = self.client.post("/delete/99999")
        self.assertEqual(res.status_code, 302)


if __name__ == "__main__":
    unittest.main()
