import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kidsmath.api import create_app
from kidsmath.render.pipeline import RenderResult


def fake_renderer(spec, out_path, voice, silent, cache_dir, style="2d"):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"not really an mp4")
    return RenderResult(out_path, spec, 12.5)


def failing_renderer(*a):
    raise RuntimeError("boom")


def wait_for(client, lid, want):
    for _ in range(100):
        body = client.get(f"/lessons/{lid}").json()
        if body["status"] in want:
            return body
        time.sleep(0.05)
    raise AssertionError(body)


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(tmp_path, renderer=fake_renderer))


def test_generate_and_fetch_video(client):
    r = client.post("/lessons", json={"topic": "addition", "grade": 0, "numbers": [3, 2], "silent": True})
    assert r.status_code == 202
    lid = r.json()["id"]
    assert r.json()["spec"]["facts"]["result"] == 5
    done = wait_for(client, lid, {"done"})
    assert done["video_url"] == f"/lessons/{lid}/video" and done["duration"] == 12.5
    v = client.get(f"/lessons/{lid}/video")
    assert v.status_code == 200 and v.headers["content-type"] == "video/mp4"
    assert client.get(f"/lessons/{lid}/spec").json()["topic"] == "addition"


def test_invalid_requests_get_422(client):
    assert client.post("/lessons", json={"topic": "fractions"}).status_code == 422
    assert client.post("/lessons", json={"topic": "addition", "grade": 0, "numbers": [8, 7]}).status_code == 422
    assert client.post("/lessons", json={"topic": "addition", "grade": 9}).status_code == 422
    assert client.post("/lessons", json={"topic": "addition", "voice": "-o /etc/passwd"}).status_code == 422


def test_from_spec_validates_math(client):
    good = client.post("/lessons", json={"topic": "addition", "numbers": [3, 2]}).json()["spec"]
    assert client.post("/lessons/from-spec?silent=true", json=good).status_code == 202
    good["facts"]["result"] = 99
    bad = client.post("/lessons/from-spec", json=good)
    assert bad.status_code == 422 and "issues" in bad.json()["detail"]
    good["steps"][0]["actions"] = [{"type": "python", "code": "print(1)"}]
    assert client.post("/lessons/from-spec", json=good).status_code == 422


def test_unknown_and_malformed_ids(client):
    assert client.get(f"/lessons/{uuid.uuid4().hex}").status_code == 404
    assert client.get("/lessons/..%2f..%2fetc").status_code in (404, 422)
    assert client.get("/lessons/not-a-real-id/video").status_code == 422


def test_video_not_ready_then_failure_reported(tmp_path):
    c = TestClient(create_app(tmp_path, renderer=failing_renderer))
    lid = c.post("/lessons", json={"topic": "counting", "silent": True}).json()["id"]
    body = wait_for(c, lid, {"failed"})
    assert "boom" in body["error"]
    assert c.get(f"/lessons/{lid}/video").status_code == 410


def test_topics_and_health(client):
    assert client.get("/health").json() == {"ok": True}
    assert "word_problem" in client.get("/topics").json()["topics"]


def test_3d_style_accepted_and_unsupported_topics_rejected(client):
    ok = client.post("/lessons", json={"topic": "addition", "numbers": [3, 2], "style": "3d", "silent": True})
    assert ok.status_code == 202
    assert "balls" in " ".join(s["narration"] for s in ok.json()["spec"]["steps"])
    bad = client.post("/lessons", json={"topic": "shapes", "style": "3d"})
    assert bad.status_code == 422 and "3D" in bad.json()["detail"]
    assert client.post("/lessons", json={"topic": "addition", "style": "4d"}).status_code == 422
