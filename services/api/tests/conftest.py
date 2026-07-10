import os
from pathlib import Path

os.environ["SIGNALDESK_DATABASE_URL"] = "sqlite:///./test_signaldesk.db"
os.environ["SIGNALDESK_SEED_DEMO_DATA"] = "false"
os.environ["SIGNALDESK_AUTO_CREATE_SCHEMA"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from signaldesk.database import Base, get_session, make_engine
from signaldesk.main import app
from signaldesk.models import Policy


@pytest.fixture
def db(tmp_path: Path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add_all(
            [
                Policy(
                    slug="incident-test",
                    title="Incident Response",
                    category="incident",
                    language="en",
                    content="Outages require an incident owner and immediate escalation.",
                ),
                Policy(
                    slug="access-test",
                    title="Least Privilege",
                    category="access",
                    language="en",
                    content="Access requires approval, minimum permissions, and an expiry date.",
                ),
                Policy(
                    slug="service-test",
                    title="Service Requests",
                    category="service",
                    language="ar",
                    content="يجب التحقق من مقدم الطلب وتأكيد تنفيذ الخدمة.",
                ),
            ]
        )
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture
def client(tmp_path: Path):
    engine = make_engine(f"sqlite:///{tmp_path / 'api.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as seed_session:
        seed_session.add_all(
            [
                Policy(
                    slug="incident-test",
                    title="Incident Response",
                    category="incident",
                    language="en",
                    content="Outages require an incident owner and immediate escalation.",
                ),
                Policy(
                    slug="access-test",
                    title="Least Privilege",
                    category="access",
                    language="en",
                    content="Access requires approval and minimum permissions.",
                ),
            ]
        )
        seed_session.commit()

    def override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()
