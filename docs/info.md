# Tiny Dual-Channel DRAM-PIM Controller

This project is a compact standard-cell DRAM-PIM controller architecture for TinyTapeout IHP.

It exposes a 32-bit SPI command interface and implements two logical channels. Each channel has two banks, two 8-bit rows per bank, configurable refresh state with readback and auto-refresh enable control, an 18-bit accumulator, one pending command slot, and a lane-serial PIM datapath.

Implemented operations are `ACT`, `PRE`, `WR`, `RD`, `REF`, `STATUS`, `CONFIG`, `ABORT`, `NOP`, `VXOR`, `VAND`, `VOR`, `VADD`, `VSUB`, `DOT`, `MAC`, `SUM`, `POPCNT`, `XNORDOT`, `STREAM.DOT`, `STREAM.MAC`, and accumulator byte reads. `DOT`, `MAC`, and `STREAM` use unsigned INT1 bit semantics or signed INT2/INT4/INT8 lane semantics and are computed through a lane-serial accumulator datapath.
