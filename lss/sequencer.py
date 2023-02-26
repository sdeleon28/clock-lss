import asyncio
import time
from typing import Iterable
import math

import mido

from lss.midi import ControlMessage, NoteMessage, ClockMessage
from lss.utils import LSS_ASCII, FunctionPad, open_output, register_signal_handler


class Sequencer:
    def __init__(self, launchpad, debug: bool = False):
        # Create virtual MiDI device where sequencer sends signals
        self.midi_outport = open_output("Launchpad Step Sequencer", virtual=True, autoreset=True)
        register_signal_handler(self._sig_handler)

        # Setup launchpad
        self.launchpad = launchpad
        self.launchpad.hand_shake()
        self._show_lss()
        self._held_keys_from_host: set[int] = set()

        # Sequencer state and control
        self._tempo = 120  # bpm
        self._running = True
        self._debug = debug
        self._position = 0
        self._num_clocks = 0
        self._prev_step = 0

    def _sig_handler(self, signum, frame):
        print("\nExiting...")
        self.launchpad.close()
        self._running = False
        self.midi_outport.close()

    def _show_lss(self) -> None:
        """Show LSS when starting sequencer"""
        pads = [61, 51, 41, 31, 32, 65, 54, 45, 34, 68, 57, 48, 37]
        for pad in pads:
            self.launchpad.get_pad(pad).blink()
        time.sleep(1.5)
        self.launchpad.reset_all_pads()

    async def _sleep(self) -> None:
        while self._prev_step == self._position:
            await asyncio.sleep(0.001)
        self._prev_step = self._position

    def on(self, note: int, color: int = 4) -> None:
        self.launchpad.on(note, color)

    def off(self, note: int) -> None:
        self.launchpad.off(note)

    async def _process_msg(self, msg) -> None:
        if self._debug:
            print(f"Processing incoming message: {msg}")

        if ControlMessage.is_control(msg):
            self._process_control_message(msg)
            return

        if NoteMessage.is_note(msg):
            self._process_pad_message(msg)
            return

    async def _process_host_msg(self, msg) -> None:
        if self._debug:
            print(f"Processing incoming HOST message: {msg}")

        if ControlMessage.is_control(msg):
            # self._process_host_control_message(msg)
            return

        if NoteMessage.is_note(msg):
            self._process_host_note_message(msg)
            return

        if ClockMessage.is_clock(msg):
            self._process_host_clock_message(msg)

    def _process_control_message(self, msg: ControlMessage) -> None:
        if msg.value != 127:
            return

        if msg.control in FunctionPad.TEMPO_PADS:
            self.adjust_tempo(msg.control)
            return

        # Last control column for muting
        if (msg.control - 9) % 10 == 0:
            self._mute(msg.control)
            return

    def _process_host_note_message(self, msg: NoteMessage) -> None:
        if msg.type == 'note_on':
            self._held_keys_from_host = self._held_keys_from_host | {msg.note}
        elif msg.type == 'note_off':
            self._held_keys_from_host = self._held_keys_from_host - {msg.note}

    def _process_host_clock_message(self, msg: ClockMessage) -> None:
        if msg.type == 'clock':
            self._num_clocks += 1
            if self._num_clocks % 12 == 0:
                self._position = (self._position + 1) % 8 if self._running else self._position
            self._running = True
        elif msg.type == 'songpos':
            self._num_clocks = 0
            # songpos is expressed in 16th notes
            current_bar_0_indexed = math.floor(msg.pos / 16)
            next_position_in_16ths = msg.pos - (current_bar_0_indexed * 16)
            next_position_in_8ths = math.floor(next_position_in_16ths / 2)
            self._position = next_position_in_8ths
        elif msg.type == 'stop':
            self._num_clocks = 0
            self._running = False
        elif msg.type == 'continue':
            self._num_clocks = 0
            self._running = True
        elif self._debug:
            print(f'We don''t know about this clock message type: {msg}')

    def _process_pad_message(self, msg: NoteMessage) -> None:
        if msg.velocity == 0:
            return

        pad = self.launchpad.get_pad(msg.note)
        if not pad:
            return
        if pad.is_function_pad:
            return
        pad.click()

    def _mute(self, msg: int) -> None:
        """All pads in last right column are used to mute corresponding row"""
        y = int((msg - 9) / 10 - 1)
        for pad in self.launchpad.get_pads_in_row(y):
            if hasattr(pad, 'mute'):
                pad.mute()

    def adjust_tempo(self, msg: int) -> None:
        if msg == FunctionPad.ARROW_DOWN:
            self._tempo -= 5
        elif msg == FunctionPad.ARROW_UP:
            self._tempo += 5

    def send_message(self, note) -> None:
        """Send note to virtual MiDI device"""
        self.midi_outport.send(mido.Message("note_on", note=note))
        time.sleep(0.1)
        self.midi_outport.send(mido.Message("note_off", note=note))

    def _callback(self, pad):
        def pad_number_to_arp_index(pad_number):
            print(f'pad_number={pad_number}')
            vertical_notes = [43, 49, 44, 42, 39, 38, 36]
            arp_index = vertical_notes.index(pad_number) if pad_number in vertical_notes else 0
            return arp_index
        if pad.is_function_pad:
            return
        if self._running:
            index_to_pick = pad_number_to_arp_index(pad.sound.value)
            keys = sorted(list(self._held_keys_from_host))
            if keys:
                out_message = (keys * 10)[index_to_pick]
                self.send_message(out_message)

    async def _process_column(self, column: int):
        pads = self.launchpad.get_pads_in_column(column)
        await asyncio.gather(*[p.process_pad(self._callback) for p in pads])
        await self._sleep()
        await asyncio.gather(*[p.unblink() for p in pads])

    async def _process_signals(self) -> None:
        while True:
            await asyncio.gather(*[self._process_msg(m) for m in self.launchpad.get_pending_messages()])
            await asyncio.gather(*[self._process_host_msg(m) for m in self.launchpad.get_pending_messages_from_host()])
            await asyncio.sleep(0.001)

    def column_iterator(self) -> Iterable[int]:
        while True:
            yield self._position
            time.sleep(0.001)

    async def run(self) -> None:
        print(LSS_ASCII)
        print(f"Launchpad Step Sequencer is running using {self.launchpad.name}")
        asyncio.get_event_loop().create_task(self._process_signals())
        for column in self.column_iterator():
            await self._process_column(column)
