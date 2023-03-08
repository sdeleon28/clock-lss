import asyncio
from lss.midi import NoteMessage
from .channel import Channel
from .page import PadLocation, Page

CHANNELS = 8


class ChannelsManager(Channel.Listener):
    class Listener:
        def on_channel_or_page_changed(self, channel: int, page: int):
            return NotImplementedError

        def on_page_updated(self, page: Page):
            return NotImplementedError

    @property
    def legato_on(self):
        return self._legato_on

    @legato_on.setter
    def legato_on(self, value: bool):
        self._legato_on = value
        for channel in self.channels:
            channel.legato_on = value

    def add_listener(self, listener):
        self.listeners = self.listeners | {listener}

    def remove_listener(self, listener):
        self.listeners = self.listeners - {listener}

    def __init__(self, launchpad, midi_outport, debug):
        self._debug = debug
        self.launchpad = launchpad
        self._legato_on = False

        self.listeners: set[ChannelsManager.Listener] = set([])
        self.channels: list[Channel] = []
        for i in range(CHANNELS):
            channel = Channel(i, launchpad, midi_outport, debug)
            channel.add_listener(self)
            self.channels.append(channel)
        self.current_channel = 0

    def close(self):
        for channel in self.channels:
            channel.remove_listener(self)
            channel.close()

    def set_velocity(self, pad_location: PadLocation, velocity: int):
        channel = self.channels[pad_location.channel]
        page = channel.pages[pad_location.page]
        page.set_velocity(
            pad_location.x, pad_location.y, velocity)

    def proceess_host_note_message(self, msg: NoteMessage):
        for channel in self.channels:
            channel.proceess_host_note_message(msg)

    def process_host_clock_message(self, msg):
        for channel in self.channels:
            channel.process_host_clock_message(msg)

    def _get_current_channel_object(self):
        return self.channels[self.current_channel]

    def get_current_page(self):
        return self._get_current_channel_object().get_current_page()

    def set_page(self, page: int):
        self._get_current_channel_object().set_page(page)
        if self._debug:
            print(self._get_current_channel_object().get_current_page())
        self._notify_channel_or_page_changed()

    def set_channel(self, channel: int):
        self.current_channel = channel
        channel_object = self._get_current_channel_object()
        channel_object.init_controller_params()
        for c in self.channels:
            c.is_active = False
        channel_object.is_active = True
        if self._debug:
            print(self._get_current_channel_object())
        self._notify_channel_or_page_changed()

    def on_page_updated(self, page: Page):
        if (page.channel == self.current_channel):
            for listener in self.listeners:
                listener.on_page_updated(page)

    def on_page_changed(self, pagenum: int):
        self._notify_channel_or_page_changed()

    def _notify_channel_or_page_changed(self):
        for listener in self.listeners:
            listener.on_channel_or_page_changed(
                self.current_channel,
                self.get_current_page().number)

    def copy_to_next_page(self):
        self._get_current_channel_object().copy_to_next_page()
        self._notify_channel_or_page_changed()

    def toggle_pad_by_note(self, note: int):
        return self.channels[self.current_channel].toggle_pad_by_note(note)

    async def process_controller_message(self, msg) -> None:
        for channel in self.channels:
            await channel.process_controller_message(msg)

    async def run(self):
        await asyncio.gather(*[channel.run() for channel in self.channels])
