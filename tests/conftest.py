import os
import re
import tempfile
from collections.abc import Generator

import pytest


_temp_dir = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = f"sqlite:///{_temp_dir.name}/test.db"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-not-used-in-production"
os.environ["SEED_ADMIN"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402


def extract_csrf(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "CSRF token not found"
    return match.group(1)


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.add_all(
            [
                User(
                    name="测试管理员",
                    phone="19900000001",
                    password_hash=hash_password("Test@123456"),
                    role="admin",
                ),
                User(
                    name="测试员工",
                    phone="19900000002",
                    password_hash=hash_password("Test@123456"),
                    role="staff",
                ),
            ]
        )
        db.commit()
    yield


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, phone: str = "19900000001") -> None:
    page = client.get("/login")
    token = extract_csrf(page.text)
    response = client.post(
        "/login",
        data={"phone": phone, "password": "Test@123456", "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303


@pytest.fixture
def admin_client(client: TestClient) -> TestClient:
    login(client)
    return client


@pytest.fixture
def staff_client(client: TestClient) -> TestClient:
    login(client, "19900000002")
    return client


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    _temp_dir.cleanup()
