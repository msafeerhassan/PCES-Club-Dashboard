from app.utils.permissions import (
    can_manage_member,
    can_manage_submission,
    can_view_submission,
    visible_departments,
)
from app.models.submission import Submission


def test_president_can_manage_anyone(app, president, dept_admin_a):
    assert can_manage_member(president, dept_admin_a) is True


def test_department_admin_cannot_manage_president(app, president, dept_admin_a):
    assert can_manage_member(dept_admin_a, president) is False


def test_department_admin_cannot_manage_other_department_admin(app, dept_admin_a, db):
    from app.models.member import Member
    from app.models.enums import RoleEnum
    other_admin = Member(name="Other Admin", email="other@test.com", role=RoleEnum.DEPARTMENT_ADMIN)
    db.session.add(other_admin)
    db.session.commit()
    assert can_manage_member(dept_admin_a, other_admin) is False


def test_department_admin_cannot_manage_faculty_advisor(app, dept_admin_a, faculty_advisor):
    assert can_manage_member(dept_admin_a, faculty_advisor) is False


def test_department_admin_manages_own_department_member(app, dept_admin_a, member_a):
    assert can_manage_member(dept_admin_a, member_a) is True


def test_department_admin_cannot_manage_other_department_member(app, dept_admin_a, member_b):
    assert can_manage_member(dept_admin_a, member_b) is False


def test_visible_departments_scoped_correctly(app, dept_admin_a, dept_a, dept_b):
    visible = visible_departments(dept_admin_a)
    assert dept_a in visible
    assert dept_b not in visible


def test_submission_scoped_to_its_own_department_not_members_other_departments(app, db, dept_admin_a, dept_a, dept_b, member_multi):
    """Regression test for the cross-department submission leak found this session:
    a submission tied to dept_a must NOT be manageable by an admin of dept_b,
    even though the submitting member also belongs to dept_b."""
    submission = Submission(member_id=member_multi.id, department_id=dept_a.id, title="Test Project")
    db.session.add(submission)
    db.session.commit()

    assert can_manage_submission(dept_admin_a, submission) is True

    from app.models.member import Member
    from app.models.enums import RoleEnum
    admin_b = Member(name="Admin B", email="adminb@test.com", role=RoleEnum.DEPARTMENT_ADMIN)
    admin_b.departments = [dept_b]
    db.session.add(admin_b)
    db.session.commit()

    assert can_manage_submission(admin_b, submission) is False


def test_member_can_always_view_own_submission(app, db, member_a, dept_a):
    submission = Submission(member_id=member_a.id, department_id=dept_a.id, title="Own Project")
    db.session.add(submission)
    db.session.commit()
    assert can_view_submission(member_a, submission) is True