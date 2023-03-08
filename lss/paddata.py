from lss.notetype import NoteType


def _get_color_intensity_for_velocity(colors: list[int], velocity: int):
    return int((velocity / 127) * (len(colors) - 1))


def get_color_for_velocity(colors: list[int], velocity: int):
    return colors[_get_color_intensity_for_velocity(colors, velocity)]

class PadData:
    def __init__(self, note, is_on, velocity=127, note_type=NoteType.FULL):
        self.note = note
        self.is_on = is_on
        self.velocity = velocity
        self.note_type = note_type

    def __copy__(self):
        return PadData(self.note, self.is_on, self.velocity, self.note_type)

    @property
    def color(self):
        from lss.devices.launchpad_colours import Color
        return get_color_for_velocity(Color.GREEN, self.velocity)

    def __str__(self):
        return f"PadData(note={self.note}, is_on={self.is_on}, velocity={self.velocity}, note_type={self.note_type})"

