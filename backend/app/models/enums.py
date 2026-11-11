from enum import Enum, StrEnum


class EntryType(StrEnum):
    REFUEL = "refuel"
    FUEL_REMOVED = "fuel_removed"


class FillType(StrEnum):
    FULL = "full"
    PARTIAL = "partial"


class OdometerStatus(StrEnum):
    OK = "ok"
    FAULTY = "faulty"
    ESTIMATED = "estimated"


class EntrySource(StrEnum):
    MANUAL = "manual"
    EXCEL = "excel"
    TEXT_IMPORT = "text_import"


class OdometerEventType(StrEnum):
    FAULTY_PERIOD = "faulty_period"
    REPLACED = "replaced"
    RESET = "reset"


def enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]
