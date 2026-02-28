import enum


class SupplierStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"


class RequestStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ROUND_1_OPEN = "ROUND_1_OPEN"
    ROUND_1_CLOSED = "ROUND_1_CLOSED"
    ROUND_N_OPEN = "ROUND_N_OPEN"
    ROUND_N_CLOSED = "ROUND_N_CLOSED"
    DECISION = "DECISION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RoundType(str, enum.Enum):
    INITIAL = "INITIAL"
    NEGOTIATION = "NEGOTIATION"


class InvitationStatus(str, enum.Enum):
    SENT = "SENT"
    OPENED = "OPENED"
    RESPONDED = "RESPONDED"


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    ROUND_START = "ROUND_START"
    ROUND_CLOSE = "ROUND_CLOSE"
    OFFER_SUBMITTED = "OFFER_SUBMITTED"
    REPORT_GENERATED = "REPORT_GENERATED"
