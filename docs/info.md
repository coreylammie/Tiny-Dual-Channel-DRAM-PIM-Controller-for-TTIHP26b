# Tiny Dual-Channel DRAM-PIM Controller

This project is a compact standard-cell DRAM-PIM controller architecture for TinyTapeout IHP.

It exposes a 32-bit SPI command interface and implements two logical channels. Each channel has two banks, two 8-bit rows per bank, fixed-period refresh state with auto-refresh enable readback/control, an 18-bit accumulator, one pending command slot, and a lane-serial PIM datapath.

Implemented operations are `ACT`, `PRE`, `WR`, `RD`, `REF`, `STATUS`, `CONFIG`, `ABORT`, `NOP`, `VXOR`, `VADD`, `DOT`, `MAC`, and accumulator byte reads. `DOT` and `MAC` use unsigned INT1 bit semantics or signed INT2/INT4/INT8 lane semantics and are computed through a lane-serial accumulator datapath.
