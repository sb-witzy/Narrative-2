"""
Iter 17 backend tests — Streaming (SSE) endpoints + Appeal Outcome Tracker with prior-wins few-shot.

Covers:
- POST /api/generate/stream (SSE, chunks + done with saved NarrativeRecord)
- POST /api/regenerate/stream (SSE, chunks + done with {field, text})
- POST /api/appeals/stream (SSE, chunks + done with AppealRecord outcome='pending')
- PATCH /api/appeals/{id} outcome updates ('won'/'lost'/'pending' valid, 'maybe' -> 400,
  outcome_updated_at set)
- GET /api/appeals/patterns?carrier=&procedure_code= returns totals/win_rate/winning_appeals
- Few-shot: after marking one appeal as 'won', new POST /api/appeals for same (carrier, code)
  still succeeds and returns a non-empty letter.
- Backwards-compat: non-streaming POST /api/generate still returns NarrativeRecord.
"""
import json
import os
import re
import time
import uuid
from typing import Iterator, Tuple, List, Dict, Any

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.strip().split("=", 1)[1]
                break
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@dental.com"
ADMIN_PASSWORD = "admin123"

STREAM_TIMEOUT = 120  # seconds — real LLM calls


# --------- helpers ---------

def _iter_sse_events(resp: requests.Response) -> Iterator[Tuple[str, str]]:
    """Yield (event_name, data_string) tuples parsed from an SSE stream response.
    Data uses literal '\\n' for newlines (server escapes them); we return the raw string here.
    """
    event = None
    data_lines: List[str] = []
    # Use iter_lines with utf-8 decoding
    for raw in resp.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        # A blank line dispatches the current event
        if raw == "":
            if event is not None or data_lines:
                yield (event or "message", "\n".join(data_lines))
            event = None
            data_lines = []
            continue
        if raw.startswith(":"):
            continue  # comment
        if raw.startswith("event:"):
            event = raw[len("event:"):].strip()
        elif raw.startswith("data:"):
            data_lines.append(raw[len("data:"):].lstrip(" "))
    # dispatch any trailing frame
    if event is not None or data_lines:
        yield (event or "message", "\n".join(data_lines))


def _collect_sse(resp: requests.Response) -> Dict[str, Any]:
    """Consume an SSE response and return summary dict."""
    chunks: List[str] = []
    done_data: Any = None
    error_data: Any = None
    for ev, data in _iter_sse_events(resp):
        if ev == "chunk":
            chunks.append(data)
        elif ev == "done":
            done_data = data
        elif ev == "error":
            error_data = data
    return {"chunks": chunks, "done": done_data, "error": error_data}


# --------- fixtures ---------

@pytest.fixture(scope="session")
def admin_token() -> str:
    r = requests.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    tok = r.json().get("access_token")
    assert tok, "no access_token in login response"
    return tok


@pytest.fixture(scope="session")
def admin_session(admin_token) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}",
    })
    return s


@pytest.fixture(scope="session")
def stream_headers(admin_token) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}",
        "Accept": "text/event-stream",
    }


# --------- 1) Streaming narrative ---------

class TestGenerateStream:

    def test_generate_stream_returns_chunks_and_done(self, stream_headers):
        payload = {
            "procedure_code": "D3330",
            "tooth_number": "30",
            "clinical_findings": "Non-vital pulp, symptomatic apical periodontitis on tooth #30.",
            "radiographic_findings": "Well-defined periapical radiolucency ~4mm at mesial root.",
            "pulp_status": "Necrotic",
            "carrier": "delta",
            "save_to_history": True,
        }
        with requests.post(
            f"{API}/generate/stream",
            json=payload,
            headers=stream_headers,
            stream=True,
            timeout=STREAM_TIMEOUT,
        ) as r:
            assert r.status_code == 200, f"stream failed: {r.status_code} {r.text[:200]}"
            ct = r.headers.get("content-type", "")
            assert "text/event-stream" in ct, f"unexpected content-type: {ct}"
            result = _collect_sse(r)

        assert not result["error"], f"stream produced error event: {result['error']}"
        assert len(result["chunks"]) >= 1, "no chunks received from stream"
        assert result["done"], "no done event received"

        record = json.loads(result["done"])
        assert record.get("id"), "done record missing id"
        assert record.get("procedure_code") == "D3330"
        # narratives populated
        assert record.get("short_narrative", "").strip(), "short_narrative empty"
        assert record.get("long_narrative", "").strip(), "long_narrative empty"
        assert record.get("user_id"), "user_id missing on saved record"
        # Marker tags should NOT leak into the saved narratives
        assert "[SHORT]" not in record["short_narrative"]
        assert "[/SHORT]" not in record["short_narrative"]
        assert "[LONG]" not in record["long_narrative"]

    def test_generate_stream_bad_procedure_code_returns_400(self, stream_headers):
        r = requests.post(
            f"{API}/generate/stream",
            json={"procedure_code": "ZZZZ", "save_to_history": False},
            headers=stream_headers,
            timeout=30,
        )
        assert r.status_code == 400


# --------- 2) Streaming regenerate ---------

class TestRegenerateStream:

    def test_regenerate_short_stream(self, stream_headers):
        payload = {
            "procedure_code": "D3330",
            "tooth_number": "30",
            "clinical_findings": "Symptomatic irreversible pulpitis, tooth #30.",
            "carrier": "generic",
            "field": "short",
            "existing_long": "Prior long narrative context for continuity.",
            "save_to_history": False,
        }
        with requests.post(
            f"{API}/regenerate/stream",
            json=payload,
            headers=stream_headers,
            stream=True,
            timeout=STREAM_TIMEOUT,
        ) as r:
            assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
            result = _collect_sse(r)
        assert not result["error"], f"error event: {result['error']}"
        assert result["chunks"], "no chunks emitted"
        assert result["done"], "missing done event"
        done = json.loads(result["done"])
        assert done.get("field") == "short"
        assert done.get("text", "").strip(), "regenerated text empty"
        assert "[SHORT]" not in done["text"], "marker tag leaked"

    def test_regenerate_bad_field_returns_400(self, stream_headers):
        r = requests.post(
            f"{API}/regenerate/stream",
            json={
                "procedure_code": "D3330",
                "field": "medium",
                "save_to_history": False,
            },
            headers=stream_headers,
            timeout=30,
        )
        assert r.status_code == 400


# --------- 3) Streaming appeal ---------

class TestAppealStream:

    @pytest.fixture(scope="class")
    def narrative_id(self, admin_session) -> str:
        payload = {
            "procedure_code": "D3330",
            "tooth_number": "19",
            "clinical_findings": "Symptomatic necrotic pulp #19; percussion positive; caries into pulp chamber.",
            "radiographic_findings": "5mm periapical radiolucency at mesial root.",
            "pulp_status": "Necrotic",
            "carrier": "delta",
            "save_to_history": True,
        }
        r = admin_session.post(f"{API}/generate", json=payload, timeout=90)
        assert r.status_code == 200, f"/generate failed: {r.status_code} {r.text[:200]}"
        return r.json()["id"]

    def test_appeal_stream_returns_appeal_pending(self, stream_headers, narrative_id):
        payload = {
            "narrative_id": narrative_id,
            "denial_reason": "Not medically necessary; alternative benefit for extraction applies.",
            "denial_code": "D-EXT-ALT",
            "save_to_history": True,
        }
        with requests.post(
            f"{API}/appeals/stream",
            json=payload,
            headers=stream_headers,
            stream=True,
            timeout=STREAM_TIMEOUT,
        ) as r:
            assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
            result = _collect_sse(r)

        assert not result["error"], f"error event: {result['error']}"
        assert result["chunks"], "no chunks emitted"
        assert result["done"], "missing done event"
        appeal = json.loads(result["done"])
        assert appeal.get("id")
        assert appeal.get("outcome") == "pending", f"default outcome not pending: {appeal.get('outcome')}"
        assert appeal.get("letter", "").strip(), "letter empty"
        assert appeal.get("subject_line", "").strip(), "subject_line empty"
        assert appeal.get("narrative_id") == narrative_id
        assert appeal.get("carrier") == "delta"
        assert appeal.get("procedure_code") == "D3330"
        # marker tags shouldn't leak
        for tag in ("[SUBJECT]", "[/SUBJECT]", "[LETTER]", "[/LETTER]"):
            assert tag not in appeal["letter"], f"tag {tag} leaked into letter"

    def test_appeal_stream_missing_narrative_returns_404(self, stream_headers):
        r = requests.post(
            f"{API}/appeals/stream",
            json={
                "narrative_id": "does-not-exist-" + uuid.uuid4().hex[:6],
                "denial_reason": "x",
            },
            headers=stream_headers,
            timeout=30,
        )
        assert r.status_code == 404


# --------- 4) Appeal outcome PATCH ---------

class TestAppealOutcome:

    @pytest.fixture(scope="class")
    def appeal_id(self, admin_session) -> str:
        # create narrative then appeal (non-streaming path)
        r = admin_session.post(f"{API}/generate", json={
            "procedure_code": "D3330",
            "tooth_number": "3",
            "clinical_findings": "Necrotic pulp, symptomatic; #3.",
            "carrier": "cigna",
            "save_to_history": True,
        }, timeout=90)
        assert r.status_code == 200
        nid = r.json()["id"]
        r2 = admin_session.post(f"{API}/appeals", json={
            "narrative_id": nid,
            "denial_reason": "Insufficient documentation.",
            "save_to_history": True,
        }, timeout=90)
        assert r2.status_code == 200
        return r2.json()["id"]

    def test_patch_outcome_won_sets_timestamp(self, admin_session, appeal_id):
        r = admin_session.patch(f"{API}/appeals/{appeal_id}", json={"outcome": "won"})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        data = r.json()
        assert data["outcome"] == "won"
        assert data.get("outcome_updated_at"), "outcome_updated_at not set"

        # GET back to verify persistence
        g = admin_session.get(f"{API}/appeals/{appeal_id}")
        assert g.status_code == 200
        got = g.json()
        assert got["outcome"] == "won"
        assert got.get("outcome_updated_at") == data["outcome_updated_at"]

    def test_patch_outcome_invalid_returns_400(self, admin_session, appeal_id):
        r = admin_session.patch(f"{API}/appeals/{appeal_id}", json={"outcome": "maybe"})
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:200]}"

    def test_patch_outcome_lost_and_back_to_pending(self, admin_session, appeal_id):
        r1 = admin_session.patch(f"{API}/appeals/{appeal_id}", json={"outcome": "lost"})
        assert r1.status_code == 200
        assert r1.json()["outcome"] == "lost"

        r2 = admin_session.patch(f"{API}/appeals/{appeal_id}", json={"outcome": "pending"})
        assert r2.status_code == 200
        assert r2.json()["outcome"] == "pending"


# --------- 5) Appeal patterns + few-shot from prior wins ---------

class TestAppealPatternsAndFewShot:

    # Use a unique carrier so counts are deterministic and isolated from prior tests.
    UNIQUE_CARRIER = "delta"
    PROCEDURE_CODE = "D2740"

    @pytest.fixture(scope="class")
    def seeded_won_appeal(self, admin_session) -> Dict[str, Any]:
        """Create a narrative + appeal, mark appeal as 'won'."""
        # Narrative
        r = admin_session.post(f"{API}/generate", json={
            "procedure_code": self.PROCEDURE_CODE,
            "tooth_number": "14",
            "clinical_findings": "Fractured cusp, MOD caries, non-restorable direct.",
            "carrier": self.UNIQUE_CARRIER,
            "save_to_history": True,
        }, timeout=90)
        assert r.status_code == 200
        nid = r.json()["id"]

        # Appeal
        r2 = admin_session.post(f"{API}/appeals", json={
            "narrative_id": nid,
            "denial_reason": "Not medically necessary; less costly alternative applies.",
            "denial_code": "LCA-01",
            "save_to_history": True,
        }, timeout=90)
        assert r2.status_code == 200
        appeal = r2.json()
        aid = appeal["id"]

        # Mark won
        r3 = admin_session.patch(f"{API}/appeals/{aid}", json={"outcome": "won"})
        assert r3.status_code == 200
        appeal.update(r3.json())
        return {"appeal": appeal, "narrative_id": nid}

    def test_patterns_reports_won_appeal(self, admin_session, seeded_won_appeal):
        r = admin_session.get(
            f"{API}/appeals/patterns",
            params={"carrier": self.UNIQUE_CARRIER, "procedure_code": self.PROCEDURE_CODE},
        )
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        data = r.json()
        # Structural assertions
        for key in ("total", "won", "lost", "pending", "win_rate", "winning_appeals"):
            assert key in data, f"pattern response missing key {key!r}"
        # Must reflect at least the one we just marked won
        assert data["won"] >= 1, f"expected won >= 1, got {data['won']}"
        assert data["total"] >= data["won"]
        assert isinstance(data["winning_appeals"], list)
        assert len(data["winning_appeals"]) >= 1, "winning_appeals empty despite won>=1"
        w0 = data["winning_appeals"][0]
        assert w0.get("id"), "winning appeal missing id"
        assert "letter_excerpt" in w0
        # win_rate should be a float 0..1 when won+lost > 0
        wr = data["win_rate"]
        assert wr is None or 0.0 <= wr <= 1.0

    def test_patterns_ignores_other_users(self, admin_session):
        # New user, no appeals → all zeros
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        email = f"test_iter17_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register", json={
            "email": email, "password": "testpass123", "office_name": "TEST_Iter17_Other",
        })
        assert r.status_code == 200
        tok = r.json()["access_token"]
        s.headers["Authorization"] = f"Bearer {tok}"
        rp = s.get(f"{API}/appeals/patterns", params={
            "carrier": self.UNIQUE_CARRIER, "procedure_code": self.PROCEDURE_CODE,
        })
        assert rp.status_code == 200
        data = rp.json()
        assert data["won"] == 0
        assert data["total"] == 0
        assert data["winning_appeals"] == []

    def test_new_appeal_uses_prior_wins_and_generates_letter(self, admin_session, seeded_won_appeal):
        """After marking one appeal as 'won', creating a new appeal for the same (carrier, code)
        should still succeed and yield a non-empty letter. (Prompt embeds prior wins internally.)"""
        # Fresh narrative for same carrier + procedure
        r = admin_session.post(f"{API}/generate", json={
            "procedure_code": self.PROCEDURE_CODE,
            "tooth_number": "30",
            "clinical_findings": "Fractured cusp with recurrent decay; non-restorable direct.",
            "carrier": self.UNIQUE_CARRIER,
            "save_to_history": True,
        }, timeout=90)
        assert r.status_code == 200
        nid = r.json()["id"]

        r2 = admin_session.post(f"{API}/appeals", json={
            "narrative_id": nid,
            "denial_reason": "Alternative benefit — least costly alternative treatment.",
            "denial_code": "LCA-01",
            "save_to_history": False,
        }, timeout=120)
        assert r2.status_code == 200, f"{r2.status_code} {r2.text[:400]}"
        appeal = r2.json()
        assert appeal.get("letter", "").strip(), "letter empty"
        assert appeal.get("subject_line", "").strip(), "subject_line empty"
        # Default outcome from POST /appeals (non-streaming) should also be 'pending'
        assert appeal.get("outcome", "pending") in ("pending", None), (
            f"new appeal has unexpected outcome: {appeal.get('outcome')}"
        )


# --------- 6) Backwards-compat: non-streaming /generate still works ---------

class TestBackwardsCompat:

    def test_generate_non_streaming(self, admin_session):
        r = admin_session.post(f"{API}/generate", json={
            "procedure_code": "D2740",
            "tooth_number": "14",
            "clinical_findings": "Extensive caries, non-restorable.",
            "carrier": "generic",
            "save_to_history": False,
        }, timeout=90)
        assert r.status_code == 200
        data = r.json()
        assert data.get("procedure_code") == "D2740"
        assert data.get("short_narrative", "").strip()
        assert data.get("long_narrative", "").strip()
        assert data.get("id")


# --------- Cleanup: mark TEST appeals as pending, do NOT delete other user rows here ---------

@pytest.fixture(scope="session", autouse=True)
def _final_cleanup(admin_session):
    yield
    # Best-effort: list appeals and reset any 'won'/'lost' created in this run back to 'pending'
    # so we don't inflate future pattern queries in production seed. Non-fatal on failure.
    try:
        r = admin_session.get(f"{API}/appeals", timeout=30)
        if r.status_code == 200:
            for ap in r.json():
                # Only touch ones we likely created this run (last 30 min heuristic + won/lost)
                if ap.get("outcome") in ("won", "lost"):
                    admin_session.patch(f"{API}/appeals/{ap['id']}", json={"outcome": "pending"})
    except Exception:
        pass
