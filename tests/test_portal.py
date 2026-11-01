"""API authorization and artifact boundaries, without launching scientific jobs."""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import json
from pathlib import Path
import tempfile
import unittest
from fastapi.testclient import TestClient
from pmda.portal import create_app
from pmda.store import Store

ROOT = Path(__file__).resolve().parents[1]


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / "runtime")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.app = create_app(root / "portal", {"workspace": {"name":"Workspace", "root":root / "campaigns", "readonly":False}, "other":{"name":"Other", "root":root / "other", "readonly":False}})
        self.addCleanup(lambda: self.app.state.pool.shutdown(wait=True))
        self.app.state.add_user("viewer", "Local-test-password!", "viewer", ["workspace"])
        self.app.state.add_user("operator", "Local-test-password!", "operator", ["workspace"])
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.store = Store(root / "campaigns")
        self.cid = self.store.create("Public-data test campaign")
        self.path = f"/api/v1/projects/workspace/campaigns/{self.cid}"

    def login(self, username="viewer"):
        result = self.client.post("/api/v1/login", json={"username":username,"password":"Local-test-password!"})
        self.assertEqual(result.status_code, 200)
        return {"X-CSRF-Token":result.json()["csrf"]}

    def test_anonymous_and_security_headers(self):
        self.assertEqual(self.client.get(self.path).status_code,401)
        response = self.client.get("/")
        self.assertEqual(response.status_code,200)
        self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])

    def test_role_and_csrf(self):
        headers = self.login()
        self.assertEqual(self.client.post(self.path + "/launch").status_code,403)
        self.assertEqual(self.client.post(self.path + "/launch",headers=headers).status_code,403)
        self.assertEqual(self.store.get(self.cid)["state"],"DRAFT")

    def test_operator_cannot_skip_approval(self):
        headers = self.login("operator")
        self.assertEqual(self.client.post(self.path + "/launch",headers=headers).status_code,409)
        self.assertEqual(self.store.get(self.cid)["state"],"DRAFT")

    def test_project_isolation(self):
        self.login()
        self.assertEqual(self.client.get("/api/v1/projects/other/campaigns").status_code,404)
        self.assertEqual(len(self.client.get("/api/v1/projects").json()),1)

    def test_download_traversal_and_missing_molecule(self):
        self.login()
        self.assertEqual(self.client.get(self.path+"/download",params={"path":"../../portal/portal.sqlite3"}).status_code,404)
        self.assertEqual(self.client.get(self.path+"/molecule/-1").status_code,404)

    def test_cross_origin_and_logout(self):
        headers = self.login()
        self.assertEqual(self.client.post("/api/v1/logout",headers=headers|{"Origin":"https://attacker.example"}).status_code,403)
        self.assertEqual(self.client.post("/api/v1/logout",headers=headers).status_code,200)
        self.assertEqual(self.client.get(self.path).status_code,401)

    def test_candidate_pagination_and_filter(self):
        folder = self.store.root / self.cid / "evaluation"
        folder.mkdir()
        rows = [dict(row=i,input_smiles="CCO",valid=True,passes_configured_gates=i%2==0,rejection_reasons=[],activity={"status":"unavailable"}) for i in range(10000)]
        (folder / "evaluation.json").write_text(json.dumps({"rows":rows,"summary":{"total":len(rows)}}),encoding="utf-8")
        self.login()
        response = self.client.get(self.path+"/candidates",params={"passed":"true","offset":10,"limit":25})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()["total"],5000)
        self.assertEqual(len(response.json()["rows"]),25)
        self.assertEqual(response.json()["rows"][0]["row"],20)


if __name__ == "__main__":
    unittest.main()
