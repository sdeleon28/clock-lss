# Clock-based Launchpad Step Sequencer

Fork of https://github.com/turbaszek/lss that syncs to a host's clock and customizes
behavior quite a bit.

This particular fork combines sequencer and arpeggiator features in a way that fits my
needs.

I will probably document this better once it does useful stuff.

## Installation

To install locally run:

```sh
pip install -e .
```

Then start the sequencer by running

```sh
lss run --device-type=<DEVICE_NAME>
```

To list supported devices run:

```sh
lss devices list
```

## Reference

- [Novation Launchpad Mini MK3 programming guide](https://www.djshop.gr/Attachment/DownloadFile?downloadId=10737)
- [Mido documentation](https://mido.readthedocs.io)
