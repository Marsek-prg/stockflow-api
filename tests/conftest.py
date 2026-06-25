from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.deps import get_db
from app.main import app
from app.models.user import User, UserRole

ADMIN_PASSWORD_HASH = hash_password("admin-password")


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    db = testing_session()

    yield db

    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def anonymous_client(db_session: Session) -> Generator[TestClient, None, None]:

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client(anonymous_client: TestClient, db_session: Session) -> TestClient:
    admin = User(
        email="admin@example.com",
        hashed_password=ADMIN_PASSWORD_HASH,
        full_name="Test Admin",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    anonymous_client.headers["Authorization"] = (
        f"Bearer {create_access_token(str(admin.id))}"
    )
    return anonymous_client
