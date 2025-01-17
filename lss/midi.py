import mido


class HexMessage(mido.Message):
    """
    Example of documented message:

    Host => Launchpad Mini [MK3]:
    Hex: F0h 00h 20h 29h 02h 0Dh 00h 7Fh F7h
    Dec: 240 0 32 41 2 13 0 127 247

    Strips first and last control byte. Just copy paste the msg from
    Novation programming manual.
    """

    def __init__(self, msg: str):
        data = map(int, msg.split(" ")[1:-1])
        super().__init__("sysex", data=data)


class ControlMessage(mido.Message):
    control: int
    value: int

    @staticmethod
    def is_control(msg):
        return hasattr(msg, "control") and hasattr(msg, "value")


class NoteMessage(mido.Message):
    velocity: int
    note: int
    type: str

    @staticmethod
    def is_note(msg):
        return hasattr(msg, "velocity") and hasattr(msg, "note")


class ClockMessage(mido.Message):
    type: str
    pos: int

    @staticmethod
    def is_clock(msg):
        return getattr(msg, "type", None) in ["clock", "songpos", "continue", "stop"]
