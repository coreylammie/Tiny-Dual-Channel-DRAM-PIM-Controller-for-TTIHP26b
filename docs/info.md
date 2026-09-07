# Tiny Dual-Channel DRAM-PIM Controller

This project is a compact standard-cell DRAM-PIM controller architecture for TinyTapeout IHP.

It exposes a 32-bit SPI command interface and implements two logical channels. Each channel has two banks, two 8-bit rows per bank, fixed-period refresh state with auto-refresh enable readback/control, and a 14-bit accumulator. One lane-serial PIM datapath is shared between the channels.

Implemented operations are `ACT`, `PRE`, `WR`, `RD`, `REF`, `STATUS`, `CONFIG`, `ABORT`, `NOP`, `VADD`, `DOT`, `MAC`, and accumulator byte reads. `DOT` and `MAC` use unsigned INT1 bit semantics or signed INT2/INT4 lane semantics and are computed through the shared lane-serial accumulator datapath. INT8 compute is reserved in the area-reduced 1x1 target.
