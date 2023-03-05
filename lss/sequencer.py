import asyncio
import time

from lss.channels_manager import ChannelsManager
from lss.midi import ControlMessage, NoteMessage, ClockMessage
from lss.utils import LSS_ASCII, open_output, register_signal_handler
from .page import Page, PadLocation
from lss.devices.launchpad_layout import LaunchpadLayout

# TODO: Move this into a config file (that is shared across features, see PARAMS constant in lss/channel.py)
VELOCITY_CC = 12


class Sequencer(ChannelsManager.Listener):
    def __init__(self, launchpad, debug: bool = False):
        self._debug = debug
        self._done = False

        # Create virtual MiDI device where sequencer sends signals
        self.midi_outport = open_output(
            "Launchpad Step Sequencer", virtual=True, autoreset=True)
        register_signal_handler(self._sig_handler)

        # Setup launchpad
        self.launchpad = launchpad
        self.launchpad.hand_shake()
        self._show_lss()
        self.launchpad_layout = LaunchpadLayout()
        self.channels_manager = ChannelsManager(
            launchpad, self.midi_outport, debug)
        self.channels_manager.add_listener(self)
        self.launchpad.set_page(self.channels_manager.get_current_page())
        self.last_pad_location: PadLocation | None = None

    def on_channel_or_page_changed(self, channel: int, page: int):
        self.launchpad.reset_all_pads()
        self.launchpad.set_channel_number(channel)
        self.launchpad.set_page_number(page)
        self.launchpad.set_page(self.channels_manager.get_current_page())

    def on_page_updated(self, page: Page):
        self.launchpad.set_page(page)

    def _sig_handler(self, signum, frame):
        print("\nExiting...")
        self._done = True
        self.channels_manager.close()
        self.channels_manager.remove_listener(self)
        self.launchpad.close()
        self._running = False
        self.midi_outport.close()

    def _show_lss(self) -> None:
        """Show LSS when starting sequencer"""
        self.launchpad.reset_all_pads()
        pads = [61, 51, 41, 31, 32, 65, 54, 45, 34, 68, 57, 48, 37]
        self.launchpad.blink_pads(pads)
        time.sleep(1.5)
        self.launchpad.reset_all_pads()

    async def _process_controller_message(self, msg) -> None:
        if msg.control == VELOCITY_CC and self.last_pad_location:
            self.channels_manager.set_velocity(
                self.last_pad_location, msg.value)
        await self.channels_manager.process_controller_message(msg)

    def _process_control_message(self, msg: ControlMessage) -> None:
        if self._debug:
            print('CONTROL message: {}'.format(msg))
        if msg.value != 127:
            return
        if self.launchpad_layout.is_menu_pad(msg.control):
            self._process_menu_pad(msg.control)

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

    def _process_host_note_message(self, msg: NoteMessage) -> None:
        self.channels_manager.proceess_host_note_message(msg)

    def _process_host_clock_message(self, msg: ClockMessage) -> None:
        self.channels_manager.process_host_clock_message(msg)

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
            current_page = self.channels_manager.get_current_page()
            self.last_pad_location = current_page.toggle_pad_by_note(msg.note)
            self.launchpad.init_controller_param(VELOCITY_CC, 127)

    async def _process_msg(self, msg) -> None:
        if self._debug:
            print(f"Processing incoming message: {msg}")

        if ControlMessage.is_control(msg):
            self._process_control_message(msg)
            return

        if NoteMessage.is_note(msg):
            self._process_pad_message(msg)
            return

    async def _process_signals(self) -> None:
        while not self._done:
            await asyncio.gather(*[self._process_msg(m) for m in self.launchpad.get_pending_messages()])
            await asyncio.gather(*[self._process_host_msg(m) for m in self.launchpad.get_pending_messages_from_host()])
            await asyncio.gather(*[self._process_controller_message(m) for m in self.launchpad.get_pending_controller_messages()])
            await asyncio.sleep(0.001)

    async def run(self) -> None:
        print(LSS_ASCII)
        print(
            f"Launchpad Step Sequencer is running using {self.launchpad.name}")
        asyncio.get_event_loop().create_task(self._process_signals())
        await self.channels_manager.run()
