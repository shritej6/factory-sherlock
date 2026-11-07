import os
from datetime import timedelta

import jwt
import pytest
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.repositories.sql_loader import UnknownQueryError, load_query, load_sql, query_names


def test_password_hashes_are_salted_and_verifiable() -> None:
    first, second = hash_password("secret"), hash_password("secret")
    assert first != second
    assert verify_password("secret", first) and verify_password("secret", second)
    assert not verify_password("wrong", first)
    assert not verify_password("secret", "not-a-bcrypt-hash")


def test_tokens_round_trip_and_reject_tampering(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-secret-with-at-least-thirty-two-bytes")
    get_settings.cache_clear()
    token = create_access_token(user_id=42, role="ENGINEER")
    payload = decode_access_token(token)
    assert payload["sub"] == "42" and payload["role"] == "ENGINEER"
    with pytest.raises(AuthenticationError):
        decode_access_token(token + "x")
    expired = jwt.encode(
        {
            "sub": "42",
            "iat": jwt.api_jwt.datetime.now(jwt.api_jwt.timezone.utc) - timedelta(minutes=2),
            "exp": jwt.api_jwt.datetime.now(jwt.api_jwt.timezone.utc) - timedelta(minutes=1),
        },
        "unit-test-secret-with-at-least-thirty-two-bytes",
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError, match="expired"):
        decode_access_token(expired)
    missing_claims = jwt.encode(
        {"sub": "42"}, "unit-test-secret-with-at-least-thirty-two-bytes", algorithm="HS256"
    )
    with pytest.raises(AuthenticationError, match="invalid"):
        decode_access_token(missing_claims)
    get_settings.cache_clear()
    os.environ.pop("JWT_SECRET_KEY", None)


def test_sql_catalog_contains_every_documented_query() -> None:
    names = query_names()
    assert len(names) == 13
    assert "machine_defect_rate_comparison" in names
    assert "characteristic_control_chart" in names
    assert "investigation.shared_material_lots" in names
    assert load_sql("unit_backward_trace").startswith("-- Query 05")
    assert load_sql("characteristic_control_chart").startswith("-- Query 10")
    clause = load_query("investigation.shared_material_lots", expanding=("batch_ids",))
    assert ":batch_ids" in clause.text
    with pytest.raises(UnknownQueryError):
        load_sql("does_not_exist")
