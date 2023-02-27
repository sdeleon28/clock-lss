import asyncio
import time
from typing import Iterable
import math
from copy import copy

import mido
from lss.channels_manager import ChannelsManager
from lss.clock_math import get_page_for_tick, get_page_position_for_tick

from lss.midi import ControlMessage, NoteMessage, ClockMessage
from lss.utils import LSS_ASCII, open_output, register_signal_handler
from .page import Page
from lss.devices.launchpad_layout import LaunchpadLayout


CLOCKS_PER_EIGHTH = 12


class Param:
    def __init__(self, attribute_name, name, control, min_value, max_value):
        self.attribute_name = attribute_name
        self.name = name
        self.control = control
        self.min_value = min_value
        self.max_value = max_value


PARAMS = [
    Param('_octave_shift', 'Octave', 15, -4, 4),
    Param('_rate', 'Rate', 14, 1, 3),
    Param('_gate', 'Gate', 13, 0, 100),
]


def shift_octaves(note: int, octaves=0):
    return note + (octaves * 12)


def clip_to_range(n, min_val, max_val):
    return max(min_val, min(n, max_val))


def control_message_to_proportion(num):
    max_control = 127
    if num < 0 or num > max_control:
        raise ValueError("Input must be between 0 and 255")
    res = round(num/float(max_control) * 1.1, 2)
    return clip_to_range(res, 0, 1)


def get_value_from_proportion(proportion, min_val, max_val):
    if proportion < 0 or proportion > 1:
        raise ValueError("Proportion must be between 0 and 1")
    return min_val + (max_val - min_val) * proportion


def get_proportion_from_value(value, min_val, max_val):
    if value < min_val or value > max_val:
        raise ValueError(
            "Value must be between {} and {}".format(min_val, max_val))
    return (value - min_val) / (max_val - min_val)


def snap(number, array):
    closest_index = min(range(len(array)),
                        key=lambda i: abs(array[i] - number))
    closest_value = array[closest_index]
    return closest_index, closest_value


class QueueMessage:
    def __init__(self, channel, note):
        self.channel = channel
        self.note = note

    def __copy__(self):
        return QueueMessage(self.channel, self.note)


class Sequencer(ChannelsManager.Listener):
    def __init__(self, launchpad, debug: bool = False):
        self._done = False

        # Sequencer state and control
        self._running = True
        self._debug = debug
        self._position = 0
        self._num_clocks = 0
        self._prev_step = 0
        self._queued_messages: list[QueueMessage] = []
        self._octave_shift = 2
        self._rate = 2
        self._held_keys_from_host: set[int] = set()
        self._gate = 100

        # Create virtual MiDI device where sequencer sends signals
        self.midi_outport = open_output(
            "Launchpad Step Sequencer", virtual=True, autoreset=True)
        register_signal_handler(self._sig_handler)

        # Setup launchpad
        self.launchpad = launchpad
        self.launchpad.hand_shake()
        self._show_lss()
        self._init_controller_params()
        self.launchpad_layout = LaunchpadLayout()
        self.channels_manager = ChannelsManager()
        self.channels_manager.add_listener(self)
        self.launchpad.set_page(self.channels_manager.get_current_page())

    def on_channel_or_page_changed(self, channel: int, page: int):
        self.launchpad.reset_all_pads()
        self.launchpad.set_channel_number(channel)
        self.launchpad.set_page_number(page)
        self.launchpad.set_page(self.channels_manager.get_current_page())

    def on_page_updated(self, page: Page):
        self.launchpad.set_page(page)

    def _init_controller_params(self):
        for param in PARAMS:
            self.launchpad.init_controller_param(param.control,
                                                 int(
                                                     get_value_from_proportion(
                                                         get_proportion_from_value(
                                                             getattr(
                                                                 self, param.attribute_name),
                                                             param.min_value,
                                                             param.max_value),
                                                         0,
                                                         127)))

    def _sig_handler(self, signum, frame):
        print("\nExiting...")
        self._done = True
        self.channels_manager.remove_listener(self)
        self.launchpad.close()
        self._running = False
        self.midi_outport.close()
        self._queued_messages = []

    def _show_lss(self) -> None:
        """Show LSS when starting sequencer"""
        self.launchpad.reset_all_pads()
        pads = [61, 51, 41, 31, 32, 65, 54, 45, 34, 68, 57, 48, 37]
        self.launchpad.blink_pads(pads)
        time.sleep(1.5)
        self.launchpad.reset_all_pads()

    async def _sleep(self) -> None:
        while not self._done and self._prev_step == self._position:
            await asyncio.sleep(0.001)
        self._prev_step = self._position

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

    async def _process_controller_message(self, msg) -> None:
        if self._debug:
            print(f"Processing incoming CONTROLLER message: {msg}")

        if ControlMessage.is_control(msg):
            if msg.control in map(lambda p: p.control, PARAMS):
                param = list(
                    filter(lambda p: p.control == msg.control, PARAMS))[0]
                octave_value = get_value_from_proportion(control_message_to_proportion(msg.value),
                                                         param.min_value,
                                                         param.max_value)
                _snapped_octave_index, snapped_octave_value = snap(
                    octave_value, range(param.min_value, param.max_value + 1))
                setattr(self, param.attribute_name, snapped_octave_value)

    def _process_control_message(self, msg: ControlMessage) -> None:
        if self._debug:
            print('CONTROL message: {}'.format(msg))
        if msg.value != 127:
            return
        if self.launchpad_layout.is_menu_pad(msg.control):
            self._process_menu_pad(msg.control)

    def _process_host_note_message(self, msg: NoteMessage) -> None:
        if msg.type == 'note_on':
            self._held_keys_from_host = self._held_keys_from_host | {msg.note}
        elif msg.type == 'note_off':
            self._held_keys_from_host = self._held_keys_from_host - {msg.note}

    def _process_host_clock_message(self, msg: ClockMessage) -> None:
        if msg.type == 'clock':
            self._num_clocks += 1
            if self._num_clocks % (CLOCKS_PER_EIGHTH / self._rate) == 0:
                self._position = self._position + 1 if self._running else self._position
            self._running = True
        elif msg.type == 'songpos':
            self._num_clocks = 0
            # songpos is expressed in 16th notes
            current_bar_0_indexed = math.floor(msg.pos / 16)
            next_position_in_16ths = msg.pos - (current_bar_0_indexed * 16)
            next_position_in_8ths = math.floor(next_position_in_16ths / 2)
            self._position = next_position_in_8ths
        elif msg.type == 'stop':
            self._position = 0
            self._num_clocks = 0
            self.channels_manager.set_page(0)
            self._running = False
        elif msg.type == 'continue':
            self._position = 0
            self._num_clocks = 0
            self.channels_manager.set_page(0)
            self._running = True
        elif self._debug:
            print(f'We don''t know about this clock message type: {msg}')

    def _process_menu_pad(self, pad):
        if pad == self.launchpad_layout.up:
            print('UP')
        if pad == self.launchpad_layout.down:
            print('DOWN')
        if pad == self.launchpad_layout.left:
            print('LEFT')
        if pad == self.launchpad_layout.right:
            self.channels_manager.copy_to_next_page()
        if pad == self.launchpad_layout.page0:
            self.channels_manager.set_page(0)
        if pad == self.launchpad_layout.page1:
            self.channels_manager.set_page(1)
        if pad == self.launchpad_layout.page2:
            self.channels_manager.set_page(2)
        if pad == self.launchpad_layout.page3:
            self.channels_manager.set_page(3)

    def _process_channel_pad(self, pad):
        if pad == self.launchpad_layout.channel0:
            self.channels_manager.set_channel(0)
        if pad == self.launchpad_layout.channel1:
            self.channels_manager.set_channel(1)
        if pad == self.launchpad_layout.channel2:
            self.channels_manager.set_channel(2)
        if pad == self.launchpad_layout.channel3:
            self.channels_manager.set_channel(3)
        if pad == self.launchpad_layout.channel4:
            self.channels_manager.set_channel(4)
        if pad == self.launchpad_layout.channel5:
            self.channels_manager.set_channel(5)
        if pad == self.launchpad_layout.channel6:
            self.channels_manager.set_channel(6)
        if pad == self.launchpad_layout.channel7:
            self.channels_manager.set_channel(7)

    def _process_pad_message(self, msg: NoteMessage) -> None:
        if msg.velocity == 0:
            return
        if self.launchpad_layout.is_channel_pad(msg.note):
            self._process_channel_pad(msg.note)
        else:
            self.channels_manager.get_current_page().toggle_pad_by_note(msg.note)

    def _mute(self, msg: int) -> None:
        """All pads in last right column are used to mute corresponding row"""
        y = int((msg - 9) / 10 - 1)
        for pad in self.launchpad.get_pads_in_row(y):
            if hasattr(pad, 'mute'):
                pad.mute()

    def send_note(self, message: QueueMessage, length=0.1) -> None:
        """Send note to virtual MiDI device"""
        self.midi_outport.send(mido.Message(
            "note_on", channel=message.channel, note=message.note))
        time.sleep(length)
        self.midi_outport.send(mido.Message(
            "note_off", channel=message.channel, note=message.note))

    def send_notes(self, messages: list[QueueMessage], length=0.1) -> None:
        """Send note to virtual MiDI device"""
        for message in messages:
            self.midi_outport.send(mido.Message(
                "note_on", channel=message.channel, note=message.note))
        time.sleep(length)
        for message in messages:
            self.midi_outport.send(mido.Message(
                "note_off", channel=message.channel, note=message.note))

    async def _callback(self, pad_number):
        if self._running and pad_number != None:
            index_to_pick = self.launchpad_layout.pad_to_arp_index(pad_number)
            keys = sorted(list(self._held_keys_from_host))
            if keys:
                keys_in_octaves: list[int] = []
                for octaves in range(8):
                    keys_in_octaves += [shift_octaves(key, octaves)
                                        for key in keys]
                out_note = keys_in_octaves[index_to_pick]
                # TODO
                channel = 0
                self._queue_message(QueueMessage(channel, out_note))

    def _queue_message(self, msg: QueueMessage):
        self._queued_messages.append(msg)

    async def _send_queued_messages(self):
        messages = []
        for msg in self._queued_messages:
            transformed_msg = copy(msg)
            transformed_msg.note = shift_octaves(msg.note, self._octave_shift)
            if transformed_msg.note >= 0 and transformed_msg.note < 128:
                messages.append(transformed_msg)
        quick_arpeggio_mode = False
        if quick_arpeggio_mode:
            # TODO: Calculate note length
            note_length = 0.1
            for message in messages:
                self.send_note(message, note_length)
        else:
            self.send_notes(messages, max(1, self._gate) / 1000.0)
        self._queued_messages = []

    async def _process_column(self, column: int):
        self.channels_manager.set_page(get_page_for_tick(column))
        pads = self.channels_manager.get_current_page().get_pads_in_column(
            get_page_position_for_tick(column))
        # TODO: Not sure this needs to be async
        await asyncio.gather(*[self._callback(p.note if p and p.is_on else None) for p in pads])
        self.launchpad.set_page(self.channels_manager.get_current_page())
        cursor_pads = map(lambda x: x.note if x else None, pads)
        self.launchpad.blink_pads(cursor_pads)
        await self._send_queued_messages()
        await self._sleep()
        self.launchpad.unblink_pads(cursor_pads)

    async def _process_signals(self) -> None:
        while not self._done:
            await asyncio.gather(*[self._process_msg(m) for m in self.launchpad.get_pending_messages()])
            await asyncio.gather(*[self._process_host_msg(m) for m in self.launchpad.get_pending_messages_from_host()])
            await asyncio.gather(*[self._process_controller_message(m) for m in self.launchpad.get_pending_controller_messages()])
            await asyncio.sleep(0.001)

    def column_iterator(self) -> Iterable[int]:
        while not self._done:
            yield self._position
            time.sleep(0.001)

    async def run(self) -> None:
        print(LSS_ASCII)
        print(
            f"Launchpad Step Sequencer is running using {self.launchpad.name}")
        asyncio.get_event_loop().create_task(self._process_signals())
        for column in self.column_iterator():
            await self._process_column(column)
