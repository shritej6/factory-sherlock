from app.models import InvestigationBatch, InvestigationEvidence
from app.repositories.sql_loader import load_sql
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

Ids = dict[str, dict[str, int]]
WINDOW = {"window_start": "2026-11-02T00:00:00", "window_end": "2026-11-04T00:00:00"}
CORE_RULES = ["R1", "R2", "R3", "R4", "R5", "R6"]


def test_high_defect_rate_is_detected_with_evidence(
    client: TestClient, engineer: dict[str, str], ids: Ids, simulated: dict[str, object]
) -> None:
    body = {"title": "CNC-03 drift", "machine_id": ids["machines"]["CNC-03"], **WINDOW}
    response = client.post("/api/v1/investigations", json=body, headers=engineer)
    assert response.status_code == 201, response.text
    inv = response.json()
    codes = [e["rule_code"] for e in inv["evidence"]]
    assert codes == ["R1", "R2", "R3", "R4", "R5", "R6"]
    assert "elevated defect rate" in inv["summary"]
    assert "Oversized diameter" in inv["summary"]
    assert "TOOL_WEAR" in inv["summary"]
    assert len(inv["batch_links"]) >= 1
    r1 = inv["evidence"][0]
    assert r1["query_name"] == "machine_defect_rate_comparison"
    assert r1["query_sql"].startswith("-- Query 01")
    assert any(
        row["machine_code"] == "CNC-03" and row["defect_rank"] == 1 for row in r1["result_rows"]
    )
    assert inv["evidence"][3]["result_rows"][0]["event_type"] == "TOOL_WEAR"


def test_healthy_machine_is_not_flagged(
    client: TestClient, engineer: dict[str, str], ids: Ids, simulated: dict[str, object]
) -> None:
    body = {"title": "CNC-01 check", "machine_id": ids["machines"]["CNC-01"], **WINDOW}
    inv = client.post("/api/v1/investigations", json=body, headers=engineer).json()
    assert "in line with" in inv["evidence"][0]["narrative"]
    assert inv["batch_links"] == []
    assert "No action is indicated" in inv["summary"]


def test_investigation_lifecycle_and_validation(
    client: TestClient, engineer: dict[str, str], operator: dict[str, str], ids: Ids
) -> None:
    bad_window = {
        "title": "x",
        "machine_id": ids["machines"]["CNC-01"],
        "window_start": "2026-11-04T00:00:00",
        "window_end": "2026-11-02T00:00:00",
    }
    assert (
        client.post("/api/v1/investigations", json=bad_window, headers=engineer).status_code == 422
    )
    assert (
        client.post(
            "/api/v1/investigations", json={"title": "x", **WINDOW}, headers=operator
        ).status_code
        == 403
    )

    inv = client.post(
        "/api/v1/investigations", json={"title": "Fleet review", **WINDOW}, headers=engineer
    ).json()
    url = f"/api/v1/investigations/{inv['id']}/status"
    assert (
        client.post(url, json={"status": "CLOSED"}, headers=engineer).status_code == 422
    )  # needs conclusion
    assert (
        client.post(url, json={"status": "IN_REVIEW"}, headers=engineer).json()["status"]
        == "IN_REVIEW"
    )
    closed = client.post(
        url, json={"status": "CLOSED", "conclusion": "No issue found."}, headers=engineer
    ).json()
    assert closed["status"] == "CLOSED" and closed["closed_at"] is not None
    assert client.post(url, json={"status": "OPEN"}, headers=engineer).status_code == 422
    assert len(client.get("/api/v1/investigations", headers=operator).json()) == 1


def test_evidence_rows_keep_sql_column_order(
    client: TestClient,
    engineer: dict[str, str],
    simulated: dict[str, object],
    ids: dict[str, dict[str, int]],
) -> None:
    body = {
        "title": "Column order check",
        "machine_id": ids["machines"]["CNC-03"],
        "window_start": "2026-11-01T00:00:00",
        "window_end": "2026-11-05T00:00:00",
    }
    inv = client.post("/api/v1/investigations", json=body, headers=engineer).json()
    r1 = inv["evidence"][0]
    assert list(r1["result_rows"][0].keys())[:3] == ["machine_id", "machine_code", "machine_name"]
    assert "T" in inv["evidence"][2]["result_rows"][0]["bucket_start"]
    assert "." not in inv["created_at"]


def _open_cnc3(client: TestClient, engineer: dict[str, str], ids: Ids) -> dict:  # type: ignore[type-arg]
    body = {"title": "CNC-03 review", "machine_id": ids["machines"]["CNC-03"], **WINDOW}
    response = client.post("/api/v1/investigations", json=body, headers=engineer)
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


def test_every_flagged_batch_comes_from_r5_and_is_linked_in_the_database(
    client: TestClient,
    engineer: dict[str, str],
    ids: Ids,
    simulated: dict[str, object],
    db_session: Session,
) -> None:
    inv = _open_cnc3(client, engineer, ids)
    cards = {e["rule_code"]: e for e in inv["evidence"]}
    assert [c for c in (e["rule_code"] for e in inv["evidence"]) if c in CORE_RULES] == CORE_RULES
    r5_ids = {row["batch_id"] for row in cards["R5"]["result_rows"]}
    assert r5_ids and all(row["machine_code"] == "CNC-03" for row in cards["R5"]["result_rows"])
    linked = {link["batch_id"] for link in inv["batch_links"]}
    assert linked == r5_ids
    assert {link["reason"] for link in inv["batch_links"]} == {"Defect rate above review threshold"}
    stored = db_session.scalars(
        select(InvestigationBatch.batch_id).where(InvestigationBatch.investigation_id == inv["id"])
    ).all()
    assert set(stored) == linked and len(stored) == len(linked)
    review = client.get(
        "/api/v1/analytics/queries/batches_requiring_review",
        params={**WINDOW, "threshold": 0.10, "machine_id": ids["machines"]["CNC-03"]},
        headers=engineer,
    ).json()["rows"]
    assert {row["batch_id"] for row in review} == r5_ids
    assert all(row["already_under_investigation"] == 1 for row in review)


def test_every_evidence_card_stores_the_exact_sql_file_and_ordered_columns(
    client: TestClient,
    engineer: dict[str, str],
    ids: Ids,
    simulated: dict[str, object],
    db_session: Session,
) -> None:
    inv = _open_cnc3(client, engineer, ids)
    assert [e["sequence"] for e in inv["evidence"]] == list(range(1, len(inv["evidence"]) + 1))
    for card in inv["evidence"]:
        assert card["query_sql"] == load_sql(card["query_name"]), card["rule_code"]
    stored = db_session.scalars(
        select(InvestigationEvidence)
        .where(InvestigationEvidence.investigation_id == inv["id"])
        .order_by(InvestigationEvidence.sequence)
    ).all()
    for row, card in zip(stored, inv["evidence"], strict=True):
        payload = row.result_rows
        assert set(payload) == {"columns", "rows"}
        if card["result_rows"]:
            assert payload["columns"] == list(card["result_rows"][0].keys())
            assert payload["rows"][0] == list(card["result_rows"][0].values())
        assert row.query_sql == load_sql(row.query_name)
    r1_columns = stored[0].result_rows["columns"]
    assert r1_columns[:3] == ["machine_id", "machine_code", "machine_name"]


def test_investigation_window_and_title_boundaries(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    machine = ids["machines"]["CNC-01"]
    equal = {
        "title": "abc",
        "machine_id": machine,
        "window_start": WINDOW["window_start"],
        "window_end": WINDOW["window_start"],
    }
    response = client.post("/api/v1/investigations", json=equal, headers=engineer)
    assert response.status_code == 422
    assert (
        "window_end must be after window_start"
        in response.json()["details"]["errors"][0]["message"]
    )
    one_second = {**equal, "window_end": "2026-11-02T00:00:01"}
    assert (
        client.post("/api/v1/investigations", json=one_second, headers=engineer).status_code == 201
    )
    short_title = {**one_second, "title": "ab"}
    assert (
        client.post("/api/v1/investigations", json=short_title, headers=engineer).status_code == 422
    )
    unknown_machine = {**one_second, "machine_id": 999999}
    assert (
        client.post("/api/v1/investigations", json=unknown_machine, headers=engineer).status_code
        == 404
    )
    unknown_product = {**one_second, "product_id": 999999}
    assert (
        client.post("/api/v1/investigations", json=unknown_product, headers=engineer).status_code
        == 404
    )


def test_investigation_can_be_reopened_from_review_but_not_after_closing(
    client: TestClient, engineer: dict[str, str]
) -> None:
    inv = client.post(
        "/api/v1/investigations", json={"title": "Reopen check", **WINDOW}, headers=engineer
    ).json()
    url = f"/api/v1/investigations/{inv['id']}/status"
    assert (
        client.post(url, json={"status": "IN_REVIEW"}, headers=engineer).json()["status"]
        == "IN_REVIEW"
    )
    reopened = client.post(url, json={"status": "OPEN"}, headers=engineer).json()
    assert reopened["status"] == "OPEN" and reopened["closed_at"] is None
    closed = client.post(
        url, json={"status": "CLOSED", "conclusion": "x" * 4000}, headers=engineer
    ).json()
    assert closed["status"] == "CLOSED" and len(closed["conclusion"]) == 4000
    too_long = client.post(
        url, json={"status": "CLOSED", "conclusion": "x" * 4001}, headers=engineer
    )
    assert too_long.status_code == 422
    for target in ("OPEN", "IN_REVIEW"):
        response = client.post(url, json={"status": target}, headers=engineer)
        assert response.status_code == 422
        assert response.json()["details"]["allowed"] == []
