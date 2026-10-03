"""HTTP API tests (FastAPI TestClient)."""

from __future__ import annotations


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["passages"] > 0
    assert body["vectors"] > 0


def test_root_reports_configuration(client):
    body = client.get("/").json()
    assert body["embedding_provider"] == "local"
    assert body["generator"] == "template"


def test_modes_endpoint(client):
    modes = client.get("/api/modes").json()
    ids = {m["id"] for m in modes}
    for expected in ["situation_advice", "moral_dilemma", "character_wisdom",
                     "source_explorer", "daily_reflection", "episode"]:
        assert expected in ids
    for m in modes:
        assert m["label"] and m["emoji"] and m["tagline"]


def test_chat_returns_structured_response(client):
    r = client.post("/api/chat", json={
        "message": "What happens in the dice game of the Mahabharata?",
        "mode": "episode",
        "language": "en",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    reply = body["reply"]

    # --- 8. response format -------------------------------------------- #
    for section in ["situation_summary", "episode", "interpretation",
                    "application", "reflection_questions", "sources",
                    "support_level", "safety_notices"]:
        assert section in reply, f"missing section {section}"
    assert reply["support_level"] != "insufficient_evidence"
    assert reply["sources"], "no sources returned"
    assert reply["primary_text"], "no evidence passages returned"
    assert len(reply["reflection_questions"]) >= 3

    # --- provenance ----------------------------------------------------- #
    assert body["citations"], "no citations persisted"
    for c in body["citations"]:
        assert c["reference"]
        assert 0.0 <= c["relevance"] <= 1.0

    # --- history --------------------------------------------------------- #
    conv_id = body["conversation_id"]
    hist = client.get(f"/api/conversations/{conv_id}").json()
    assert len(hist["messages"]) == 2
    assert hist["messages"][0]["role"] == "user"
    assert hist["messages"][1]["role"] == "assistant"
    assert hist["messages"][1]["reply"] is not None


def test_chat_continues_in_same_conversation(client):
    first = client.post("/api/chat", json={
        "message": "Why did Karna remain loyal to Duryodhana?", "mode": "character_wisdom",
        "character": "karna",
    }).json()
    second = client.post("/api/chat", json={
        "message": "What does that imply about loyalty?", "mode": "situation_advice",
        "conversation_id": first["conversation_id"],
    }).json()
    assert second["conversation_id"] == first["conversation_id"]
    hist = client.get(f"/api/conversations/{second['conversation_id']}").json()
    assert len(hist["messages"]) == 4


def test_unknown_mode_is_rejected(client):
    r = client.post("/api/chat", json={"message": "hello", "mode": "made_up"})
    assert r.status_code in (400, 422)


def test_empty_message_is_rejected(client):
    r = client.post("/api/chat", json={"message": "", "mode": "situation_advice"})
    assert r.status_code == 422


def test_conversation_listing_and_delete(client):
    created = client.post("/api/chat", json={
        "message": "Should I forgive a friend who betrayed me?",
        "mode": "situation_advice",
    }).json()
    conv_id = created["conversation_id"]
    listing = client.get("/api/conversations").json()
    assert any(c["id"] == conv_id for c in listing)
    assert client.delete(f"/api/conversations/{conv_id}").status_code == 200
    assert all(c["id"] != conv_id for c in client.get("/api/conversations").json())


def test_characters_endpoints(client):
    chars = client.get("/api/characters").json()
    slugs = {c["slug"] for c in chars}
    for expected in ["krishna", "yudhishthira", "arjuna", "bhima", "draupadi",
                     "vidura", "bhishma", "karna", "duryodhana", "gandhari",
                     "kunti", "nakula", "sahadeva", "sanjaya", "dhritarashtra",
                     "shakuni", "drona", "ashwatthama"]:
        assert expected in slugs
    detail = client.get("/api/characters/karna").json()
    assert detail["character"]["name"] == "Karna"
    assert detail["passages"], "no passages associated with Karna"
    assert "interpretation" in detail["perspective_hint"].lower()
    assert client.get("/api/characters/nope").status_code == 404


def test_themes_endpoint(client):
    themes = client.get("/api/themes").json()
    slugs = {t["slug"] for t in themes}
    assert {"dharma", "revenge", "loyalty", "forgiveness"} <= slugs
    assert any(t["passage_count"] > 0 for t in themes)


def test_source_explorer_search(client):
    r = client.post("/api/search", json={"q": "dice game gambling", "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] > 0
    top = body["results"][0]
    assert top["parva"]
    assert top["source_reference"]
    assert top["verification_status"] in {"verified", "unverified", "rejected"}

    # metadata-only browse
    browse = client.post("/api/search", json={"q": "", "parva": "Sabha", "limit": 10})
    assert browse.json()["count"] > 0
    assert all("Sabha" in x["parva"] for x in browse.json()["results"])


def test_source_explorer_applies_filters_to_hybrid_results(client):
    r = client.post("/api/search", json={
        "q": "dice game gambling",
        "parva": "Sabha",
        "character": "Yudhishthira",
        "theme": "gambling",
        "text_type": "summary",
        "verified_only": True,
        "limit": 10,
    })
    assert r.status_code == 200
    results = r.json()["results"]
    assert results
    for result in results:
        assert "Sabha" in result["parva"]
        assert "yudhishthira" in " ".join(
            [result["speaker"], result["listener"], *result["characters"]]
        ).lower()
        assert "gambling" in result["themes"]
        assert result["text_type"] == "summary"
        assert result["verification_status"] == "verified"


def test_passage_detail(client):
    results = client.post("/api/search", json={"q": "dice game", "limit": 1}).json()
    pid = results["results"][0]["id"]
    detail = client.get(f"/api/passages/{pid}").json()
    assert detail["id"] == pid
    assert detail["reference"]


def test_daily_reflection(client):
    body = client.get("/api/reflection/daily").json()
    assert "available" in body
    if body["available"]:
        reply = body["reply"]
        assert reply["primary_text"], "daily reflection must include a passage"
        assert reply["sources"]
        assert reply["support_level"] in {"strong_textual_support", "interpretive"}


def test_situation_advice_flow(client):
    """13. Example user flow, end to end."""
    r = client.post("/api/chat", json={
        "message": (
            "I have been working hard but someone else is getting the credit. "
            "I feel like giving up. What does the Mahabharata teach about this?"
        ),
        "mode": "situation_advice",
    })
    assert r.status_code == 200
    reply = r.json()["reply"]
    assert reply["support_level"] != "insufficient_evidence"
    assert reply["episode"], "no episode presented"
    assert reply["sources"]
    assert len(reply["reflection_questions"]) >= 3
    # analysis extracted the conflict
    assert reply["analysis"]["conflict"] or reply["analysis"]["values"]
    # safety disclaimer always present
    assert any(n["kind"] == "general" for n in reply["safety_notices"])


def test_perspectives_mode(client):
    r = client.post("/api/chat", json={
        "message": "Should I stay silent when my friend is doing something wrong?",
        "mode": "perspectives",
    })
    assert r.status_code == 200
    reply = r.json()["reply"]
    if reply["perspectives"]:
        for p in reply["perspectives"]:
            assert p["character"]
            assert p["stance"]
            assert p["passage_ids"]
            assert p["basis"]


def test_feedback_endpoint(client):
    created = client.post("/api/chat", json={
        "message": "What happens in the dice game?", "mode": "episode",
    }).json()
    r = client.post("/api/feedback", json={
        "message_id": created["message_id"],
        "rating": 1,
        "categories": ["grounded"],
        "comment": "clear sources",
    })
    assert r.status_code == 200 and r.json()["ok"] is True


def test_admin_stats(client):
    body = client.get("/api/admin/stats").json()
    assert body["passages"] > 0
    assert body["embeddings"] == body["passages"]
    assert body["by_verification"]
    assert body["by_parva"]


def test_admin_passage_listing_and_verify(client):
    page = client.get("/api/admin/passages", params={"limit": 5}).json()
    assert page["total"] > 0 and page["items"]
    pid = page["items"][0]["id"]
    original = page["items"][0]["verification_status"]

    r = client.post(f"/api/admin/passages/{pid}/verify",
                    json={"status": "verified", "note": "checked in tests"})
    assert r.status_code == 200
    assert r.json()["status"] == "verified"

    client.post(f"/api/admin/passages/{pid}/verify",
                json={"status": original, "note": "restored"})


def test_admin_create_edit_delete_passage(client):
    ref = "TEST Parva — a passage created by the test suite"
    payload = {
        "parva": "Test Parva",
        "section": "Unit test",
        "speaker": "Tester",
        "listener": "Reader",
        "characters": ["Tester"],
        "themes": ["dharma"],
        "keywords": ["test"],
        "summary": "A synthetic passage used only by the automated tests.",
        "source_reference": ref,
        "text_type": "summary",
    }
    created = client.post("/api/admin/passages", json=payload)
    assert created.status_code == 200, created.text
    pid = created.json()["id"]
    assert created.json()["verification_status"] == "unverified"

    # duplicate reference is rejected
    dup = client.post("/api/admin/passages", json=payload)
    assert dup.status_code == 409

    updated = client.patch(f"/api/admin/passages/{pid}", json={"summary": "Edited summary."})
    assert updated.status_code == 200
    assert updated.json()["embedding_status"] == "indexed"  # re-embedded on edit

    # verification survives only until an edit; editing a verified passage resets it
    client.post(f"/api/admin/passages/{pid}/verify", json={"status": "verified"})
    client.patch(f"/api/admin/passages/{pid}", json={"summary": "Edited again."})
    after = client.get("/api/admin/passages", params={"q": ref}).json()
    assert after["items"][0]["verification_status"] == "unverified"
    assert "re-check" in after["items"][0]["verification_note"].lower()

    deleted = client.delete(f"/api/admin/passages/{pid}")
    assert deleted.status_code == 200
    assert client.get("/api/admin/passages", params={"q": ref}).json()["total"] == 0


def test_admin_retrieval_quality(client):
    body = client.get("/api/admin/retrieval-quality").json()
    assert body["corpus_size"] > 0
    assert len(body["queries"]) >= 5
    assert isinstance(body["no_evidence_rate"], float)
    assert 0.0 <= body["no_evidence_rate"] <= 1.0
    # it must be reported as coverage, not as a confidence score
    assert "not confidence" in body["note"]


def test_auth_register_login_me(client):
    email = "tester@example.com"
    client.delete  # noqa: B018 - readability only
    reg = client.post("/api/auth/register", json={
        "email": email, "password": "secret123", "display_name": "Tester",
    })
    if reg.status_code == 409:  # already registered by a previous run
        reg = client.post("/api/auth/register", json={
            "email": "tester2@example.com", "password": "secret123",
        })
    assert reg.status_code == 200, reg.text
    token = reg.json()["token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["authenticated"] is True

    bad = client.post("/api/auth/login", json={"email": email, "password": "wrong-pass"})
    assert bad.status_code == 401


def test_docs_available(client):
    assert client.get("/openapi.json").status_code == 200
