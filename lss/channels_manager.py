from .channel import Channel
from .page import Page

CHANNELS = 8


class ChannelsManager(Channel.Listener):
    class Listener:
        def on_channel_or_page_changed(self, channel: int, page: int):
            return NotImplementedError

        def on_page_updated(self, page: Page):
            return NotImplementedError

    def add_listener(self, listener):
        self.listeners = self.listeners | {listener}

    def remove_listener(self, listener):
        self.listeners = self.listeners - {listener}

    def __init__(self):
        self._debug = False

        self.listeners: set[ChannelsManager.Listener] = set([])
        self.channels: list[Channel] = []
        for i in range(CHANNELS):
            channel = Channel(i)
            channel.add_listener(self)
            self.channels.append(channel)
        self.current_channel = 0

    def __del__(self):
        for channel in self.channels:
            channel.remove_listener(self)

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
        if self._debug:
            print(self._get_current_channel_object())
        self._notify_channel_or_page_changed()

    def on_page_updated(self, page: Page):
        if (page.channel == self.current_channel):
            for listener in self.listeners:
                listener.on_page_updated(page)

    def _notify_channel_or_page_changed(self):
        for listener in self.listeners:
            listener.on_channel_or_page_changed(
                self.current_channel,
                self.get_current_page().number)

    def copy_to_next_page(self):
        self._get_current_channel_object().copy_to_next_page()
        self._notify_channel_or_page_changed()
