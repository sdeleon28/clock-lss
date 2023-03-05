import asyncio
import time

from lss.channels_manager import ChannelsManager
from lss.midi import ControlMessage, NoteMessage, ClockMessage
from lss.utils import LSS_ASCII, open_output, register_signal_handler
from .page import Page
from lss.devices.launchpad_layout import LaunchpadLayout
from lss.devices.launchpad_colours import Color as C


class Colors(ChannelsManager.Listener):
    def __init__(self, launchpad, debug: bool = False):
        self._debug = debug
        self._done = False

        # Setup launchpad
        self.launchpad = launchpad
        self.launchpad.hand_shake()
        self.launchpad_layout = LaunchpadLayout()
        self.page = Page(0, 0)

        pad_notes = list(range(11, 19)) + list(range(21, 29)) + list(range(31, 39)) + list(range(41, 49)) + \
            list(range(51, 59)) + list(range(61, 69)) + \
            list(range(71, 79)) + list(range(81, 89))
        # pagenum = 0
        # if pagenum == 0:
        #     for note, i in zip(pad_notes, range(1, 65)):
        #         self.page.toggle_pad_by_note(note, i)
        # else:
        #     for note, i in zip(map(lambda x: x + 64, pad_notes), range(1, 65)):
        #         self.page.toggle_pad_by_note(note, i)
        # self.launchpad.set_page(self.page)

        # Test colors
        self.launchpad.unblink_pads(range(11, 11+63+16))

        # GREEN = [24, 20, 25, 26, 21, 22]
        # def get_green_index(velocity: int):
        #     return int((velocity / 127) * (len(GREEN) - 1))

        # self.launchpad.on(11, GREEN[get_green_index(0)])
        # self.launchpad.on(12, GREEN[get_green_index(64)])
        # self.launchpad.on(13, GREEN[get_green_index(127)])

        self.launchpad.on(11, C.get(C.GREEN, C.Intensity._0))
        self.launchpad.on(12, C.get(C.GREEN, C.Intensity._1))
        self.launchpad.on(13, C.get(C.GREEN, C.Intensity._2))
        self.launchpad.on(14, C.get(C.GREEN, C.Intensity._3))
        self.launchpad.on(15, C.get(C.GREEN, C.Intensity._4))
        self.launchpad.on(16, C.get(C.GREEN, C.Intensity._5))

        self.launchpad.on(21, C.get(C.AQUA, C.Intensity._0))
        self.launchpad.on(22, C.get(C.AQUA, C.Intensity._1))
        self.launchpad.on(23, C.get(C.AQUA, C.Intensity._2))
        self.launchpad.on(24, C.get(C.AQUA, C.Intensity._3))
        self.launchpad.on(25, C.get(C.AQUA, C.Intensity._4))
        self.launchpad.on(26, C.get(C.AQUA, C.Intensity._5))

        self.launchpad.on(31, C.get(C.CYAN, C.Intensity._0))
        self.launchpad.on(32, C.get(C.CYAN, C.Intensity._1))
        self.launchpad.on(33, C.get(C.CYAN, C.Intensity._2))
        self.launchpad.on(34, C.get(C.CYAN, C.Intensity._3))
        self.launchpad.on(35, C.get(C.CYAN, C.Intensity._4))
        self.launchpad.on(36, C.get(C.CYAN, C.Intensity._5))

        self.launchpad.on(41, C.get(C.PINK, C.Intensity._0))
        self.launchpad.on(42, C.get(C.PINK, C.Intensity._1))
        self.launchpad.on(43, C.get(C.PINK, C.Intensity._2))
        self.launchpad.on(44, C.get(C.PINK, C.Intensity._3))
        self.launchpad.on(45, C.get(C.PINK, C.Intensity._4))
        self.launchpad.on(46, C.get(C.PINK, C.Intensity._5))

        self.launchpad.on(51, C.get(C.YELLOW_GREEN, C.Intensity._0))
        self.launchpad.on(52, C.get(C.YELLOW_GREEN, C.Intensity._1))
        self.launchpad.on(53, C.get(C.YELLOW_GREEN, C.Intensity._2))
        self.launchpad.on(54, C.get(C.YELLOW_GREEN, C.Intensity._3))
        self.launchpad.on(55, C.get(C.YELLOW_GREEN, C.Intensity._4))
        self.launchpad.on(56, C.get(C.YELLOW_GREEN, C.Intensity._5))

        self.launchpad.on(61, C.get(C.RED_ORANGE, C.Intensity._0))
        self.launchpad.on(62, C.get(C.RED_ORANGE, C.Intensity._1))
        self.launchpad.on(63, C.get(C.RED_ORANGE, C.Intensity._2))
        self.launchpad.on(64, C.get(C.RED_ORANGE, C.Intensity._3))
        self.launchpad.on(65, C.get(C.RED_ORANGE, C.Intensity._4))
        self.launchpad.on(66, C.get(C.RED_ORANGE, C.Intensity._5))

        self.launchpad.on(71, C.get(C.BLUE_PURPLE, C.Intensity._0))
        self.launchpad.on(72, C.get(C.BLUE_PURPLE, C.Intensity._1))
        self.launchpad.on(73, C.get(C.BLUE_PURPLE, C.Intensity._2))
        self.launchpad.on(74, C.get(C.BLUE_PURPLE, C.Intensity._3))
        self.launchpad.on(75, C.get(C.BLUE_PURPLE, C.Intensity._4))
        self.launchpad.on(76, C.get(C.BLUE_PURPLE, C.Intensity._5))

    def _sig_handler(self, signum, frame):
        print("\nExiting...")
        self._done = True
        self.launchpad.close()

    def _process_control_message(self, msg: ControlMessage) -> None:
        if self._debug:
            print('CONTROL message: {}'.format(msg))
        if msg.value != 127:
            return
        if self.launchpad_layout.is_menu_pad(msg.control):
            self._process_menu_pad(msg.control)

    def next_page(self):
        raise NotImplementedError

    def _process_menu_pad(self, pad):
        if pad == self.launchpad_layout.up:
            print('UP')
        if pad == self.launchpad_layout.down:
            self.next_page()

    async def _process_msg(self, msg) -> None:
        if self._debug:
            print(f"Processing incoming message: {msg}")

        if ControlMessage.is_control(msg):
            self._process_control_message(msg)
            return

    async def _process_signals(self) -> None:
        while not self._done:
            await asyncio.gather(*[self._process_msg(m) for m in self.launchpad.get_pending_messages()])
            await asyncio.sleep(0.001)

    async def run(self) -> None:
        print(LSS_ASCII)
        print(
            f"Launchpad Step Sequencer is running using {self.launchpad.name}")
        asyncio.get_event_loop().create_task(self._process_signals())
