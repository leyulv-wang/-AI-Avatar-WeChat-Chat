from __future__ import annotations

from fastapi.testclient import TestClient

import wxbot.main as mainmod


def test_health():
    c = TestClient(mainmod.app)
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_webhook_writes_events_and_export_csv(tmp_path):
    old_data_dir = mainmod.data_dir
    old_backup_dir = mainmod.backup_dir
    old_service_dir = mainmod.service._data_dir
    try:
        mainmod.data_dir = tmp_path / "data"
        mainmod.backup_dir = tmp_path / "backups"
        mainmod.service._data_dir = mainmod.data_dir

        c = TestClient(mainmod.app)
        r = c.post(
            "/weflow/webhook",
            json={"contact_id": "wxid_test", "content": "你好", "timestamp": 1715773894},
        )
        assert r.status_code == 200

        r = c.get("/api/contacts/wxid_test/events?limit=10")
        assert r.status_code == 200
        data = r.json()["data"]
        assert any(e.get("direction") == "inbound" and e.get("content") == "你好" for e in data)

        r = c.get("/api/contacts/wxid_test/export.csv?limit=10")
        assert r.status_code == 200
        assert "timestamp,direction" in r.text

        r = c.get("/api/contacts")
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()["data"]]
        assert "wxid_test" in ids
    finally:
        mainmod.data_dir = old_data_dir
        mainmod.backup_dir = old_backup_dir
        mainmod.service._data_dir = old_service_dir


def test_role_roundtrip(tmp_path):
    old_data_dir = mainmod.data_dir
    old_service_dir = mainmod.service._data_dir
    try:
        mainmod.data_dir = tmp_path / "data"
        mainmod.service._data_dir = mainmod.data_dir

        c = TestClient(mainmod.app)
        r = c.put(
            "/api/contacts/wxid_test/role",
            json={
                "role_id": "default",
                "name": "测试",
                "personality": "友好",
                "language_style": "简洁",
                "expertise": "",
                "constraints": [],
                "example_replies": [],
            },
        )
        assert r.status_code == 200

        r = c.get("/api/contacts/wxid_test/role")
        assert r.status_code == 200
        assert r.json()["data"]["name"] == "测试"
    finally:
        mainmod.data_dir = old_data_dir
        mainmod.service._data_dir = old_service_dir


def test_profile_recompute(tmp_path):
    old_data_dir = mainmod.data_dir
    old_service_dir = mainmod.service._data_dir
    try:
        mainmod.data_dir = tmp_path / "data"
        mainmod.service._data_dir = mainmod.data_dir

        c = TestClient(mainmod.app)
        c.post("/weflow/webhook", json={"contact_id": "wxid_test", "content": "哈哈可以。"})
        r = c.post("/api/contacts/wxid_test/profile/recompute")
        assert r.status_code == 200
        assert "avg_len" in r.json()["data"]
    finally:
        mainmod.data_dir = old_data_dir
        mainmod.service._data_dir = old_service_dir


def test_candidates_endpoint(tmp_path):
    old_data_dir = mainmod.data_dir
    old_service_dir = mainmod.service._data_dir
    try:
        mainmod.data_dir = tmp_path / "data"
        mainmod.service._data_dir = mainmod.data_dir

        c = TestClient(mainmod.app)
        c.post("/weflow/webhook", json={"contact_id": "wxid_test", "content": "你好"})
        r = c.get("/api/contacts/wxid_test/candidates")
        assert r.status_code == 200
        assert "data" in r.json()
    finally:
        mainmod.data_dir = old_data_dir
        mainmod.service._data_dir = old_service_dir


def test_backup_create_and_restore(tmp_path):
    old_data_dir = mainmod.data_dir
    old_backup_dir = mainmod.backup_dir
    old_service_dir = mainmod.service._data_dir
    try:
        mainmod.data_dir = tmp_path / "data"
        mainmod.backup_dir = tmp_path / "backups"
        mainmod.service._data_dir = mainmod.data_dir

        c = TestClient(mainmod.app)
        c.post("/weflow/webhook", json={"contact_id": "wxid_test", "content": "x"})
        r = c.post("/api/backup/create")
        assert r.status_code == 200
        path = r.json()["path"]

        r = c.post("/api/backup/restore", json={"path": path})
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
    finally:
        mainmod.data_dir = old_data_dir
        mainmod.backup_dir = old_backup_dir
        mainmod.service._data_dir = old_service_dir


def test_send_message_without_weflow_send_path_returns_400():
    c = TestClient(mainmod.app)
    r = c.post("/api/messages/send", json={"contact_id": "wxid_test", "content": "hi"})
    assert r.status_code == 400
