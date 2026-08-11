import enum


class RoleEnum(enum.Enum):
    PRESIDENT = "president"
    VP_BOYS = "vp_boys"
    VP_GIRLS = "vp_girls"
    FACULTY_ADVISOR = "faculty_advisor"
    MEMBER = "member"


class SectionEnum(enum.Enum):
    BOYS = "boys"
    GIRLS = "girls"


class EventScopeEnum(enum.Enum):
    CLUB_WIDE = "club_wide"
    BOYS = "boys"
    GIRLS = "girls"