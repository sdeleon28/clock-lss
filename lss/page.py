from typing import List
from abc import ABC

class PadData:
    def __init__(self, note, is_on):
        self.note = note
        self.is_on = is_on

    def __str__(self):
        return f"PadData(note={self.note}, is_on={self.is_on})"


class Page:
    class Listener(ABC):
        def on_page_updated(self, page: "Page"):
            raise NotImplementedError
            
    def __init__(self, channel, number):
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
        self.pads[0][0] = PadData(Page.get_note(0, 0), True)
        self.note_map[Page.get_note(0, 0)] = self.pads[0][0]
        self.pads[3][0] = PadData(Page.get_note(3, 0), True)
        self.note_map[Page.get_note(3, 0)] = self.pads[3][0]
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
        self.notify_update()

    def toggle_pad(self, x, y):
        self.pads[x][y].is_on = not self.pads[x][y].is_on
        self.notify_update()

    def toggle_pad_by_note(self, note):
        self.note_map[note].is_on = not self.note_map[note].is_on
        self.notify_update()

    def on(self, note, color):
        # FIXME: Handle color here
        print("on", note, color)
        self.note_map[note] = PadData(note, True)
        self.notify_update()

    def off(self, note):
        print("off", note)
        self.note_map[note] = PadData(note, False)
        self.notify_update()

    def get_pads_in_column(self, x: int) -> List[PadData | None]:
        """Returns single column of pads, include functional buttons for better UX"""
        pads_ids = [Page.get_note(x, y) for y in range(8)]
        return [self.note_map.get(idx) for idx in pads_ids]

    def __str__(self):
        return f'Page(channel={self.channel}, number={self.number})'
