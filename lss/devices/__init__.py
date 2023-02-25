from lss.devices.launchpad_mini_3 import LaunchpadMiniMk3
from lss.devices.launchpad_mk2_12 import LaunchpadMk2_12
from lss.devices.launchpad_x import LaunchpadX

DEVICES = {
    LaunchpadMiniMk3.name: LaunchpadMiniMk3,
    LaunchpadX.name: LaunchpadX,
    LaunchpadMk2_12.name: LaunchpadMk2_12,
}

DEVICES_NAMES = DEVICES.keys()
