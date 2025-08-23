from dataclasses import dataclass
from enum import Enum


class QueueNames(str, Enum):
    LOGS = "logs"
    ALERTS = "alerts"
    TRACES = "traces"
    EVENTS = "events"
    BACKUPS = "backups"
    REPORTS = "reports"


@dataclass
class LogEntryMessage:
    service: str
    level: str
    message: str
    time: str
    host: str