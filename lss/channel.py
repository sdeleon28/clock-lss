from copy import copy
from lss.notetype import NoteType

from lss.paddata import PadData

from .page import PadLocation, Page
from lss.midi import ControlMessage, NoteMessage, ClockMessage
from lss.clock_math import get_page_for_tick, get_page_position_for_tick
from lss.devices.launchpad_layout import LaunchpadLayout

import math
import mido
import asyncio

PAGES = 4
STEPS_PER_PAGE = 8
CLOCKS_PER_EIGHTH = 12


class QueueMessage:
    def __init__(self, channel, note, velocity):
        self.channel = channel
        self.note = note
        self.velocity = velocity

    def __copy__(self):
        return QueueMessage(self.channel, self.note, self.velocity)


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


class Channel(Page.Listener):
    class Listener:
        def on_page_updated(self, page: Page):
            raise NotImplementedError

        def on_page_changed(self, pagenum: int):
            raise NotImplementedError

    @property
    def legato_on(self):
        return self._legato_on

    @legato_on.setter
    def legato_on(self, value: bool):
        if not self._legato_on and value:
            self.legato_started = False
        self._legato_on = value
        for page in self.pages:
            page.legato_on = value

    def toggle_pad_by_note(self, note: int):
        current_page = self.get_current_page()
        x, y = self.get_current_page().get_coords_from_note(note)
        if x is not None and y is not None and self.legato_on:
            if self.legato_started:
                # we must be in the same row
                if y != self._legato_y:
                    return 'not-changed'
                current_page.set_pad(x, y, PadData(
                    note,
                    not (current_page.pads[x][y] is not None and current_page.pads[x][y].is_on),
                    127,
                    NoteType.NOTE_OFF))
                self.legato_started = False
            else:
                current_page.set_pad(x, y, PadData(
                    note, not current_page.pads[x][y].is_on, 127, NoteType.NOTE_ON))
                self.legato_started = True
                self._legato_y = y
                return PadLocation(current_page.channel.number, current_page.number, x, y)
        elif not self.legato_started:
            return self.get_current_page().toggle_pad_by_note(note)
        else:
            return 'not-changed'

    def add_listener(self, listener: Listener):
        self.listeners = self.listeners | {listener}

    def remove_listener(self, listener: Listener):
        self.listeners = self.listeners - {listener}

    def __init__(self, number, launchpad, midi_outport, debug):
        self._debug = debug
        self._done = False
        self.is_active = False
        self.midi_outport = midi_outport
        self.launchpad = launchpad
        self.launchpad_layout = LaunchpadLayout()

        self.listeners: set[Channel.Listener] = set([])
        self._legato_on = False
        self.legato_started = False

        self.number = number
        self.pages: list[Page] = []
        for i in range(PAGES):
            page = Page(self, i)
            page.add_listener(self)
            self.pages.append(page)
        self.current_page = 0

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

        self.init_controller_params()

    def close(self):
        self._done = True
        for page in self.pages:
            page.remove_listener(self)
        self._queued_messages = []

    def init_controller_params(self):
        for param in PARAMS:
            self.launchpad.init_controller_param(
                param.control,
                int(get_value_from_proportion(
                    get_proportion_from_value(
                        getattr(self, param.attribute_name),
                        param.min_value, param.max_value),
                    0,
                    127)))

    def proceess_host_note_message(self, msg: NoteMessage):
        if msg.type == 'note_on':
            self._held_keys_from_host = self._held_keys_from_host | {msg.note}
        elif msg.type == 'note_off':
            self._held_keys_from_host = self._held_keys_from_host - {msg.note}

    def process_host_clock_message(self, msg: ClockMessage) -> None:
        if msg.type == 'clock':
            # This could be calculated mathematically
            # TODO: Make rate snap to these values
            rates_to_step_sizes = {
                0.25: 48,
                0.5: 24,
                1: 12,
                2: 6,
                3: 3,
            }
            self._position = math.floor(
                self._num_clocks / rates_to_step_sizes[self._rate])
            self._num_clocks += 1
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
            self.set_page(0)
            self._running = False
        elif msg.type == 'continue':
            self._position = 0
            self._num_clocks = 0
            self.set_page(0)
            self._running = True
        elif self._debug:
            print(f'We don''t know about this clock message type: {msg}')

    async def _sleep(self) -> None:
        while not self._done and self._prev_step == self._position:
            await asyncio.sleep(0.001)
        self._prev_step = self._position

    def _notify_channel_or_page_changed(self):
        for listener in self.listeners:
            listener.on_page_changed(
                self.get_current_page().number)

    def set_page(self, page: int):
        self.current_page = page
        self._notify_channel_or_page_changed()

    def on_page_updated(self, page: Page):
        if page.number == self.current_page:
            for listener in self.listeners:
                listener.on_page_updated(page)

    def get_current_page(self):
        return self.pages[self.current_page]

    def copy_to_next_page(self):
        next_index = (self.current_page + 1) % PAGES
        current_page = self.pages[self.current_page]
        self.pages[next_index].remove_listener(self)
        next_page = copy(current_page)
        next_page.number = next_index
        next_page.add_listener(self)
        self.pages[next_index] = next_page
        self.set_page(next_index)

    def __str__(self):
        return f"Channel(number={self.number}, page={self.get_current_page().number})"

    async def process_controller_message(self, msg) -> None:
        if self._debug:
            print(f"Processing incoming CONTROLLER message: {msg}")

        if self.is_active and ControlMessage.is_control(msg):
            if msg.control in map(lambda p: p.control, PARAMS):
                param = list(
                    filter(lambda p: p.control == msg.control, PARAMS))[0]
                octave_value = get_value_from_proportion(control_message_to_proportion(msg.value),
                                                         param.min_value,
                                                         param.max_value)
                _snapped_octave_index, snapped_octave_value = snap(
                    octave_value, range(param.min_value, param.max_value + 1))
                setattr(self, param.attribute_name, snapped_octave_value)

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
                await self.send_note(message, note_length)
        else:
            await self.send_notes(messages, max(1, self._gate) / 1000.0)
        self._queued_messages = []

    async def send_note(self, message: QueueMessage, length=0.1) -> None:
        """Send note to virtual MiDI device"""
        # FIXME: Refactor so the QueueMessage doesn't need to capture channel anymore
        # (separate queues per channel now)
        self.midi_outport.send(mido.Message(
            "note_on", channel=message.channel, note=message.note, velocity=message.velocity))
        await asyncio.sleep(length)
        self.midi_outport.send(mido.Message(
            "note_off", channel=message.channel, note=message.note, velocity=message.velocity))

    async def send_notes(self, messages: list[QueueMessage], length=0.1) -> None:
        """Send note to virtual MiDI device"""
        for message in messages:
            self.midi_outport.send(mido.Message(
                "note_on", channel=message.channel, note=message.note, velocity=message.velocity))
        await asyncio.sleep(length)
        for message in messages:
            self.midi_outport.send(mido.Message(
                "note_off", channel=message.channel, note=message.note, velocity=message.velocity))

    async def run(self):
        async for column in self.column_iterator():
            await self._process_column(column)

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
                velocity = self.get_current_page().get_velocity_for_pad_number(pad_number)
                self._queue_message(QueueMessage(
                    self.number, out_note, velocity))

    async def _process_column(self, column: int):
        self.set_page(get_page_for_tick(column))
        pads = self.get_current_page().get_pads_in_column(
            get_page_position_for_tick(column))
        # TODO: Not sure this needs to be async
        await asyncio.gather(*[self._callback(p.note if p and p.is_on else None) for p in pads])
        if self.is_active:
            # TODO: Refactor so we don't need to know about the launchpad
            self.launchpad.set_page(self.get_current_page())
            cursor_pads = map(lambda x: x.note if x else None, pads)
            self.launchpad.blink_pads(cursor_pads)
        await self._send_queued_messages()
        await self._sleep()
        if self.is_active:
            cursor_pads = map(lambda x: x.note if x else None, pads)
            self.launchpad.unblink_pads(cursor_pads)

    async def column_iterator(self):
        while not self._done:
            yield self._position
            await asyncio.sleep(0.001)
