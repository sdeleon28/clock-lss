from typing import List
from abc import ABC
from copy import copy

# from lss.devices.launchpad_colours import Color


class PadData:
    def __init__(self, note, is_on, color=None):
        self.note = note
        self.is_on = is_on
        self.color = color

    def __copy__(self):
        return PadData(self.note, self.is_on, self.color)

    def __str__(self):
        return f"PadData(note={self.note}, is_on={self.is_on}, color={self.color})"


# FIXME: This class holds duplicate state which causes all kinds of evils
class Page:
    class Listener(ABC):
        def on_page_updated(self, page: "Page"):
            raise NotImplementedError

    def __init__(self, channel, number):
        self._debug = False
        self.channel = channel
        self.number = number
        self.note_map: dict[int, PadData] = {}
        page_column_count, page_row_count = 8, 8
        row = [PadData(i, False) for i in range(page_row_count)]
        self.pads = [row[:] for _ in range(page_column_count)]
        for x in range(page_column_count):
            for y in range(page_row_count):
                note = Page.get_note(x, y)
                self.pads[x][y] = PadData(note, False)
                self.note_map[note] = self.pads[x][y]
        for row in self.pads:
            for pad_data in row:
                self.note_map[pad_data.note] = pad_data
        self.listeners: set[Page.Listener] = set([])

    @staticmethod
    def get_note(x: int, y: int) -> int:
        return 10 * (y + 1) + x + 1

    def add_listener(self, listener: Listener):
        self.listeners = self.listeners | {listener}

    def remove_listener(self, listener: Listener):
        self.listeners = self.listeners - {listener}

    def notify_update(self):
        for listener in self.listeners:
            listener.on_page_updated(self)

    def _set_pad(self, x, y, padData: PadData):
        self.pads[x][y] = padData
        self.note_map[padData.note] = padData
        self.notify_update()

    def get_coords_from_note(self, note):
        for x in range(8):
            for y in range(8):
                if self.pads[x][y].note == note:
                    return x, y
        return None, None

    def toggle_pad_by_note(self, note, color=22):
        if self._debug:
            print(f'{self} -> toggle_pad_by_note', note)
        x, y = self.get_coords_from_note(note)
        if not x is None and not y is None:
            self._set_pad(x, y, PadData(note, not self.pads[x][y].is_on, color=color))
        self.notify_update()

    def get_pads_in_column(self, x: int) -> List[PadData | None]:
        """Returns single column of pads, include functional buttons for better UX"""
        pads_ids = [Page.get_note(x, y) for y in range(8)]
        return [self.note_map.get(idx) for idx in pads_ids]

    def __copy__(self):
        new_page = Page(self.channel, self.number)
        new_page.pads = []
        for row in self.pads:
            new_page.pads.append([copy(pad_data) for pad_data in row])
        new_page.note_map = dict(
            [(key, copy(value)) for key, value in self.note_map.items()])
        return new_page

    def __str__(self):
        pads = []
        for row in self.pads:
            pads.append([str(pad_data) for pad_data in row])
        return f'Page(channel={self.channel}, number={self.number})\n{pads}'
