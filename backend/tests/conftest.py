"""
Shared test fixtures for the Corporate Lending Automation backend.
Uses a real PostgreSQL test database (corporate_lending_test) to keep
integration tests realistic while isolating from production data.
"""

import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/corporate_lending_test",
)

from app.config import settings, BASE_DIR
from app.database.base import Base
from app.database.connection import get_db
from app.main import app
from app.core.security import hash_password


TEST_DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(db: Session):
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db: Session):
    from app.models.user import User, UserRole, UserStatus

    user = db.query(User).filter(User.email == "test_admin@test.com").first()
    if not user:
        user = User(
            email="test_admin@test.com",
            hashed_password=hash_password("TestAdmin@1234"),
            full_name="Test Admin",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@pytest.fixture()
def auth_headers(client: TestClient, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test_admin@test.com", "password": "TestAdmin@1234"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
