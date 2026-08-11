from functools import wraps
from flask import abort
from flask_login import current_user
from app.models.enums import RoleEnum, SectionEnum, EventScopeEnum

ADMIN_ROLES = (RoleEnum.PRESIDENT, RoleEnum.VP_BOYS, RoleEnum.VP_GIRLS)
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


def visible_sections(member):
    if member.role in VIEW_ALL_ROLES:
        return [SectionEnum.BOYS, SectionEnum.GIRLS]
    if member.role == RoleEnum.VP_BOYS:
        return [SectionEnum.BOYS]
    if member.role == RoleEnum.VP_GIRLS:
        return [SectionEnum.GIRLS]
    return []


def can_manage_section(member, section):
    if member.role == RoleEnum.PRESIDENT:
        return True
    if member.role == RoleEnum.VP_BOYS:
        return section == SectionEnum.BOYS
    if member.role == RoleEnum.VP_GIRLS:
        return section == SectionEnum.GIRLS
    return False


def is_read_only_admin(member):
    return member.role == RoleEnum.FACULTY_ADVISOR

def assignable_roles(actor):
    if actor.role == RoleEnum.PRESIDENT:
        return list(RoleEnum)
    if actor.role in (RoleEnum.VP_BOYS, RoleEnum.VP_GIRLS):
        return [RoleEnum.MEMBER]
    return []


def assignable_sections(actor):
    if actor.role == RoleEnum.PRESIDENT:
        return [SectionEnum.BOYS, SectionEnum.GIRLS]
    if actor.role == RoleEnum.VP_BOYS:
        return [SectionEnum.BOYS]
    if actor.role == RoleEnum.VP_GIRLS:
        return [SectionEnum.GIRLS]
    return []

def can_view_event(member, event):
    if event.scope == EventScopeEnum.CLUB_WIDE:
        return True
    if member.role in VIEW_ALL_ROLES:
        return True
    if member.section is None:
        return False
    return event.scope.value == member.section.value


def assignable_event_scopes(actor):
    if actor.role == RoleEnum.PRESIDENT:
        return list(EventScopeEnum)
    if actor.role == RoleEnum.VP_BOYS:
        return [EventScopeEnum.BOYS]
    if actor.role == RoleEnum.VP_GIRLS:
        return [EventScopeEnum.GIRLS]
    return []

def can_manage_event(actor, event):
    if event.scope == EventScopeEnum.CLUB_WIDE:
        return actor.role == RoleEnum.PRESIDENT
    return can_manage_section(actor, SectionEnum(event.scope.value))