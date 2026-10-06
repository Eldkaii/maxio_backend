"""Standalone checks: temporary files and isolated FastAPI route, no .env or DB."""
import ast
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.testclient import TestClient
from src.services.simulator_log_service import MAX_READ_BYTES, read_simulator_log


def load_function(path, name, scope):
    # Execute the real route and permission guard, excluding imports that start
    # configuration/database initialization. Authentication identities are fixtures.
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, "exec"), scope)


class LogFiles(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".local"
        base.mkdir(exist_ok=True)
        self.folder = tempfile.TemporaryDirectory(prefix="log-check-", dir=base)
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)
        (self.base / "logs").mkdir()
        self.path = self.base / "logs/activity-simulator.log"

    def read(self, limit=200):
        return read_simulator_log(limit, base_dir=self.base)

    def test_absent_and_empty(self):
        self.assertEqual(self.read(), dict(available=False, lines=[], truncated=False, updated_at=None))
        self.path.write_text("", encoding="utf-8")
        self.assertTrue(self.read()["available"])
        self.assertEqual(self.read()["lines"], [])

    def test_recent_lines_across_rotation_in_chronological_order(self):
        self.path.write_text("5: Nicolás\n6: Crea liga\n", encoding="utf-8")
        self.path.with_suffix(".log.1").write_text("3\n4\n", encoding="utf-8")
        self.path.with_suffix(".log.2").write_text("1\n2\n", encoding="utf-8")
        data = self.read(5)
        self.assertEqual(data["lines"], ["2", "3", "4", "5: Nicolás", "6: Crea liga"])
        self.assertTrue(data["truncated"])
        self.assertTrue(data["updated_at"].endswith("+00:00"))

    def test_bounded_read_and_incomplete_last_record(self):
        self.path.write_bytes(b"x" * (MAX_READ_BYTES + 50) + "\nAcción completa\r\nIncompleta".encode())
        data = self.read()
        self.assertEqual(data["lines"], ["Acción completa"])
        self.assertTrue(data["truncated"])

    def test_does_not_read_state_or_unrelated_logs(self):
        (self.base / "logs/app.log").write_text("private", encoding="utf-8")
        (self.base / "activity-simulator.json").write_text("private", encoding="utf-8")
        self.assertFalse(self.read()["available"])

    def test_limit_validation(self):
        for limit in (0, 501, -1):
            with self.assertRaises(ValueError):
                self.read(limit)

    def test_permission_errors_are_not_silently_empty(self):
        with patch("pathlib.Path.open", side_effect=PermissionError("private path")):
            with self.assertRaises(PermissionError):
                self.read()


class AdminEndpoint(unittest.TestCase):
    def setUp(self):
        def identity(authorization: str | None = Header(default=None)):
            if authorization not in ("Bearer admin-fixture", "Bearer player-fixture"):
                raise HTTPException(401)
            return SimpleNamespace(is_admin=authorization == "Bearer admin-fixture")

        self.read = Mock(return_value={"available": False, "lines": [], "truncated": False, "updated_at": None})
        scope = dict(User=SimpleNamespace, Depends=Depends, Query=Query, Response=Response,
                     HTTPException=HTTPException, get_current_user=identity, read_simulator_log=self.read,
                     router=APIRouter(prefix="/users"))
        load_function("src/services/admin_service.py", "require_global_admin", scope)
        load_function("src/routers/user_router.py", "admin_simulator_log", scope)
        app = FastAPI()
        app.include_router(scope["router"], prefix="/maxio")
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def get(self, token=None, query=""):
        return self.client.get("/maxio/users/admin/simulator/log" + query,
                               headers={"Authorization": "Bearer " + token} if token else {})

    def test_authentication_and_admin_role_precede_file_read(self):
        self.assertEqual(self.get().status_code, 401)
        self.assertEqual(self.get("player-fixture").status_code, 403)
        self.read.assert_not_called()

    def test_admin_can_read_without_caching(self):
        response = self.get("admin-fixture", "?limit=100")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.read.assert_called_once_with(100)

    def test_query_rejects_unbounded_reads(self):
        for query in ("?limit=501", "?limit=0", "?limit=no"):
            self.assertEqual(self.get("admin-fixture", query).status_code, 422)
        self.read.assert_not_called()

    def test_io_error_is_sanitized(self):
        self.read.side_effect = PermissionError("internal filesystem detail")
        response = self.get("admin-fixture")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("internal filesystem detail", response.text)


if __name__ == "__main__":
    unittest.main()
