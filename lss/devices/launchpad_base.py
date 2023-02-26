from typing import Dict, List

import mido

from lss.pad import Pad
from lss.utils import open_input, open_output


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
        self.reset_all_pads()

    def hand_shake(self):
        raise NotImplementedError()

    def close(self):
        self.reset_all_pads()
        self._inport.close()
        self._outport.close()
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

    def get_pending_messages(self):
        return self._inport.iter_pending()

    def get_pending_messages_from_host(self):
        return self._host_inport.iter_pending()

    def get_pending_controller_messages(self):
        return self._controller_inport.iter_pending()
