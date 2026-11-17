from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_and_catalog():
    assert client.get("/api/health").json()["ok"] is True
    cat = client.get("/api/catalog").json()
    assert len(cat["reagents"]) > 150 and len(cat["equipment"]) >= 15
    ex = client.get("/api/experiments").json()
    assert len(ex["experiments"]) >= 190


def test_setup_and_step():
    res = client.post("/api/setup/ppt-silver-halides").json()
    bench = res["bench"]
    step = client.post("/api/step", json={"bench": bench, "actions": [
        {"op": "reagent", "v": "t1", "reagent": "AgNO3_01", "amount": 2}], "dt": 1.0}).json()
    assert any(s["id"] == "AgCl" for s in step["views"]["t1"]["solids"])


def test_step_rejects_garbage():
    r = client.post("/api/step", json={"bench": {"vessels": {"x": {"type": "nope"}, "y": "zz"}}, "actions": [
        {"op": "reagent", "v": "missing", "reagent": "HCl_1", "amount": 5}, "junk"], "dt": 1e9})
    assert r.status_code == 200
    assert r.json()["errors"]
    r = client.post("/api/step", content=b"not json", headers={"content-type": "application/json"})
    assert r.status_code == 400
