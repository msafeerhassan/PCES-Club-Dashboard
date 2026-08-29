from functools import wraps
from flask import abort
from flask_login import current_user
from app.models.enums import RoleEnum

ADMIN_ROLES = (RoleEnum.PRESIDENT, RoleEnum.DEPARTMENT_ADMIN)
VIEW_ALL_ROLES = (RoleEnum.PRESIDENT, RoleEnum.FACULTY_ADVISOR)


def roles_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


def admin_required(view_func):
    return roles_required(*ADMIN_ROLES)(view_func)


def is_read_only_admin(member):
    return member.role == RoleEnum.FACULTY_ADVISOR


def visible_departments(member):
    if member.role in VIEW_ALL_ROLES:
        from app.models.department import Department
        return Department.query.order_by(Department.name).all()
    if member.role == RoleEnum.DEPARTMENT_ADMIN:
        return list(member.departments)
    return []


def can_manage_department(actor, department):
    if actor.role == RoleEnum.PRESIDENT:
        return True
    if actor.role == RoleEnum.DEPARTMENT_ADMIN:
        return department in actor.departments
    return False


def can_manage_member(actor, member):
    if actor.role == RoleEnum.PRESIDENT:
        return True
    if actor.role == RoleEnum.DEPARTMENT_ADMIN:
        if member.role != RoleEnum.MEMBER:
            return False
        actor_ids = {d.id for d in actor.departments}
        member_ids = {d.id for d in member.departments}
        return bool(actor_ids & member_ids)
    return False


def assignable_roles(actor):
    if actor.role == RoleEnum.PRESIDENT:
        return list(RoleEnum)
    if actor.role == RoleEnum.DEPARTMENT_ADMIN:
        return [RoleEnum.MEMBER]
    return []


def assignable_departments(actor):
    from app.models.department import Department
    if actor.role == RoleEnum.PRESIDENT:
        return Department.query.order_by(Department.name).all()
    if actor.role == RoleEnum.DEPARTMENT_ADMIN:
        return list(actor.departments)
    return []

def can_manage_event(actor, event):
    if actor.role == RoleEnum.PRESIDENT:
        return True
    if actor.role != RoleEnum.DEPARTMENT_ADMIN:
        return False
    if event.is_club_wide:
        return False
    actor_ids = {d.id for d in actor.departments}
    event_ids = {d.id for d in event.departments}
    return bool(actor_ids & event_ids)


def can_view_event(member, event):
    if event.is_club_wide:
        return True
    if member.role in VIEW_ALL_ROLES:
        return True
    member_ids = {d.id for d in member.departments}
    event_ids = {d.id for d in event.departments}
    return bool(member_ids & event_ids)


def assignable_event_departments(actor):
    return assignable_departments(actor)

def can_manage_submission(actor, submission):
    if actor.role == RoleEnum.FACULTY_ADVISOR:
        return False
    if actor.role == RoleEnum.PRESIDENT:
        return True
    if actor.role != RoleEnum.DEPARTMENT_ADMIN:
        return False
    if submission.department is None:
        actor_ids = {d.id for d in actor.departments}
        member_ids = {d.id for d in submission.member.departments}
        return bool(actor_ids & member_ids)
    return submission.department in actor.departments


def can_view_submission(actor, submission):
    if actor.role in VIEW_ALL_ROLES:
        return True
    if actor.id == submission.member_id:
        return True
    if actor.role != RoleEnum.DEPARTMENT_ADMIN:
        return False
    if submission.department is None:
        actor_ids = {d.id for d in actor.departments}
        member_ids = {d.id for d in submission.member.departments}
        return bool(actor_ids & member_ids)
    return submission.department in actor.departments

def department_names_for_viewer(actor, member):
    if actor.role in VIEW_ALL_ROLES:
        return member.departments
    if actor.role == RoleEnum.DEPARTMENT_ADMIN:
        actor_ids = {d.id for d in actor.departments}
        return [d for d in member.departments if d.id in actor_ids]
    if actor.id == member.id:
        return member.departments
    return []

def can_view_announcement(member, announcement):
    if announcement.is_club_wide:
        return True
    if member.role in VIEW_ALL_ROLES:
        return True
    member_ids = {d.id for d in member.departments}
    ann_ids = {d.id for d in announcement.departments}
    return bool(member_ids & ann_ids)


def can_manage_announcement(actor, announcement):
    if actor.role == RoleEnum.PRESIDENT:
        return True
    if actor.role != RoleEnum.DEPARTMENT_ADMIN:
        return False
    if announcement.is_club_wide:
        return False
    actor_ids = {d.id for d in actor.departments}
    ann_ids = {d.id for d in announcement.departments}
    return bool(actor_ids & ann_ids)