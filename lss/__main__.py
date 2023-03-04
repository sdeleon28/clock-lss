import asyncio

import click
from lss.colors import Colors

from lss.devices import DEVICES, DEVICES_NAMES
from lss.devices.launchpad_mk2_12 import LaunchpadMk2_12
from lss.sequencer import Sequencer


@click.group()
def cli():
    """Launchpad step sequencer"""


async def _run_sequencer(device_type: str, **kwargs):
    launchpad_class = DEVICES[device_type]
    launchpad = launchpad_class()
    sequencer = Sequencer(launchpad, **kwargs)
    await sequencer.run()


async def _run_colors():
    launchpad = LaunchpadMk2_12()
    colors = Colors(launchpad)
    await colors.run()


@click.command(name="run")
@click.option(
    "--device-type",
    type=click.Choice(DEVICES_NAMES, case_sensitive=False),
    help="Name of MiDI device to connect to.",
)
@click.option(
    "--debug", is_flag=True, help="Allows printing of debug information including MiDI communication."
)
def run_sequencer(device_type: str, debug: bool = False):
    """Starts step sequencer"""
    asyncio.run(_run_sequencer(device_type=device_type, debug=debug))


@click.command(name="colors")
def run_colors(debug: bool = False):
    """Starts step sequencer"""
    asyncio.run(_run_colors())


@click.group(name="devices")
def devices_group():
    """Device configuration"""


@devices_group.command(name="list")
def list_devices():
    """List supported devices"""
    for device_name in DEVICES_NAMES:
        print(f"- {device_name}")
    print()


cli.add_command(devices_group)
cli.add_command(run_sequencer)
cli.add_command(run_colors)


def main():
    cli()


if __name__ == "__main__":
    main()
