from typing import List
from abc import ABC
from copy import copy

from lss.notetype import NoteType
from lss.paddata import PadData


class PadLocation:
    def __init__(self, channel: int, page: int, x: int, y: int):
        self.channel = channel
        self.page = page
        self.x = x
        self.y = y

    def __str__(self):
        return f"PadLocation(channel={self.channel}, page={self.page}, x={self.x}, y={self.y})"


# FIXME: This class holds duplicate state which causes all kinds of evils
class Page:
    class Listener(ABC):
        def on_page_updated(self, page: "Page"):
            raise NotImplementedError

    @property
    def legato_on(self):
        return self._legato_on

    @legato_on.setter
    def legato_on(self, value: bool):
        self._legato_on = value

    def __init__(self, channel, number):
        self._debug = False
        self.channel = channel
        self.number = number
        self.note_map: dict[int, PadData] = {}
        self._legato_on = False
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

    def set_pad(self, x, y, padData: PadData):
        self.pads[x][y] = padData
        self.note_map[padData.note] = padData
        self.notify_update()

    def get_coords_from_note(self, note):
        for x in range(8):
            for y in range(8):
                if self.pads[x][y].note == note:
                    return x, y
        return None, None

    def get_velocity_for_pad_number(self, pad_number):
        return self.note_map[pad_number].velocity

    def toggle_pad_by_note(self, note):
        if self._debug:
            print(f'{self} -> toggle_pad_by_note', note)
        x, y = self.get_coords_from_note(note)
        if not x is None and not y is None:
            if self._legato_on:
                pass
            else:
                self.set_pad(x, y, PadData(
                    note, not self.pads[x][y].is_on, 127, NoteType.FULL))
        self.notify_update()
        if not x is None and not y is None and self.pads[x][y].is_on:
            return PadLocation(self.channel.number, self.number, x, y)
        else:
            return None

    def set_velocity(self, x: int, y: int, velocity: int):
        self.pads[x][y].velocity = velocity
        self.note_map[self.pads[x][y].note].velocity = velocity
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
