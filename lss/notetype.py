from enum import Enum, auto


class NoteType(Enum):
    FULL = auto()
    NOTE_ON = auto()
    NOTE_OFF = auto()
    BRIDGE = auto()
