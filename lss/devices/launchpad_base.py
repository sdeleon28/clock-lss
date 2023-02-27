from typing import Dict, List

import mido

from lss.pad import Pad
from lss.utils import open_input, open_output, Color
from .launchpad_layout import LaunchpadLayout
from ..page import Page

class BaseLaunchpad:
    row_count: int
    column_count: int

    name: str
    pads: Dict[int, "Pad"] = {}

    def __init__(self):
        self._outport = open_output(self.name, autoreset=True)
        self._controller_outport = open_output('Midi Fighter Twister', autoreset=True)
        self._inport = open_input(self.name, autoreset=True)
        self._host_inport = open_input(self.name + " Virtual Input", virtual=True, autoreset=True)
        # TODO: This has nothing to do with the launchpad, move it to a different class
        self._controller_inport = open_input('Midi Fighter Twister', autoreset=True)
        self.layout = LaunchpadLayout()
        self.reset_all_pads()
        self.set_channel_number(0)
        self.set_page_number(0)

    def hand_shake(self):
        raise NotImplementedError()

    def close(self):
        self.reset_all_pads()
        self._outport.close()
        self._controller_outport.close()
        self._inport.close()
        self._host_inport.close()
        self._controller_inport.close()

    def init_controller_param(self, control: int, value: int):
        self._controller_outport.send(mido.Message('control_change', control=control, value=value))

    def reset_all_pads(self) -> None:
        self.pads = {}
        for x in range(self.column_count):
            for y in range(self.row_count):
                pad = Pad(x, y, launchpad=self)
                pad.off()
                self.pads[pad.note] = pad

    # TODO: This should be a DTO
    def set_page(self, page: Page):
        notes_on = len(list(filter(lambda x: x.is_on, page.note_map.values())))
        page_column_count, page_row_count = 8, 8
        for x in range(page_column_count):
            for y in range(page_row_count):
                pad_data = page.pads[x][y]
                pad = Pad(x, y, launchpad=self)
                if pad_data.is_on:
                    self.on(pad_data.note, Color.GREEN)
                    pad.on()
                else:
                    self.off(pad_data.note)
                    pad.off()
                self.pads[pad_data.note] = pad

    def blink_pads(self, pads):
        for pad_number in pads:
            pad = self.pads.get(pad_number)
            if pad and not pad._is_on:
                pad.on()
                self.on(pad_number, Color.PINK)

    def unblink_pads(self, pads):
        for pad_number in pads:
            pad = self.pads.get(pad_number)
            if pad and not pad._is_on:
                pad.off()
                self.off(pad_number)

    def get_pad(self, note: int) -> "Pad":
        return self.pads.get(note)

    def get_pads_in_column(self, x: int) -> List["Pad"]:
        """Returns single column of pads, include functional buttons for better UX"""
        pads_ids = [Pad.get_note(x, y) for y in range(9)]
        return [self.pads.get(idx) for idx in pads_ids]

    def get_pads_in_row(self, y: int) -> List["Pad"]:
        """Returns single row of pads, skips functional buttons"""
        pads_ids = [Pad.get_note(x, y) for x in range(8)]
        return [self.pads.get(idx) for idx in pads_ids]

    def on(self, note: int, color: int = 4) -> None:
        self._outport.send(mido.Message("note_on", note=note, velocity=color))

    def off(self, note: int) -> None:
        self._outport.send(mido.Message("note_off", note=note))

    def control_on(self, control: int, color: int = 63) -> None:
        self._outport.send(mido.Message("control_change", control=control, value=color))

    def control_off(self, control: int) -> None:
        self._outport.send(mido.Message("control_change", control=control, value=0))

    def get_pending_messages(self):
        return self._inport.iter_pending()

    def get_pending_messages_from_host(self):
        return self._host_inport.iter_pending()

    def get_pending_controller_messages(self):
        return self._controller_inport.iter_pending()

    def _reset_channels(self):
        self.off(self.layout.channel0)
        self.off(self.layout.channel1)
        self.off(self.layout.channel2)
        self.off(self.layout.channel3)
        self.off(self.layout.channel4)
        self.off(self.layout.channel5)
        self.off(self.layout.channel6)
        self.off(self.layout.channel7)

    def _reset_pages(self):
        self.control_off(self.layout.page0)
        self.control_off(self.layout.page1)
        self.control_off(self.layout.page2)
        self.control_off(self.layout.page3)

    def set_channel_number(self, channel: int):
        self._reset_channels()
        if channel == 0:
            self.on(self.layout.channel0)
        elif channel == 1:
            self.on(self.layout.channel1)
        elif channel == 2:
            self.on(self.layout.channel2)
        elif channel == 3:
            self.on(self.layout.channel3)
        elif channel == 4:
            self.on(self.layout.channel4)
        elif channel == 5:
            self.on(self.layout.channel5)
        elif channel == 6:
            self.on(self.layout.channel6)
        elif channel == 7:
            self.on(self.layout.channel7)

    def set_page_number(self, page: int):
        self._reset_pages()
        if page == 0:
            self.control_on(self.layout.page0)
        elif page == 1:
            self.control_on(self.layout.page1)
        elif page == 2:
            self.control_on(self.layout.page2)
        elif page == 3:
            self.control_on(self.layout.page3)
