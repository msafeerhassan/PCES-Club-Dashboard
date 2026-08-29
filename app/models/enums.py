import enum


class RoleEnum(enum.Enum):
    PRESIDENT = "president"
    DEPARTMENT_ADMIN = "department_admin"
    FACULTY_ADVISOR = "faculty_advisor"
    MEMBER = "member"

class SubmissionStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"