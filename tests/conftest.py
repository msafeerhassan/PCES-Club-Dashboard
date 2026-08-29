import pytest
from app import create_app
from app.extensions import db as _db
from app.models.member import Member
from app.models.department import Department
from app.models.enums import RoleEnum


@pytest.fixture
def app():
    flask_app = create_app()
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def president(db):
    m = Member(name="President", email="president@test.com", role=RoleEnum.PRESIDENT)
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture
def faculty_advisor(db):
    m = Member(name="Faculty", email="faculty@test.com", role=RoleEnum.FACULTY_ADVISOR)
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture
def dept_a(db):
    d = Department(name="Test Dept A")
    db.session.add(d)
    db.session.commit()
    return d


@pytest.fixture
def dept_b(db):
    d = Department(name="Test Dept B")
    db.session.add(d)
    db.session.commit()
    return d


@pytest.fixture
def dept_admin_a(db, dept_a):
    m = Member(name="Admin A", email="admina@test.com", role=RoleEnum.DEPARTMENT_ADMIN)
    m.departments = [dept_a]
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture
def member_a(db, dept_a):
    m = Member(name="Member A", email="membera@test.com", role=RoleEnum.MEMBER)
    m.departments = [dept_a]
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture
def member_b(db, dept_b):
    m = Member(name="Member B", email="memberb@test.com", role=RoleEnum.MEMBER)
    m.departments = [dept_b]
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture
def member_multi(db, dept_a, dept_b):
    m = Member(name="Multi Member", email="multi@test.com", role=RoleEnum.MEMBER)
    m.departments = [dept_a, dept_b]
    db.session.add(m)
    db.session.commit()
    return m