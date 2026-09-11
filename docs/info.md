# Tiny Dual-Channel DRAM-PIM Controller

This project is a compact standard-cell DRAM-PIM controller architecture for TinyTapeout IHP.

It exposes a 32-bit SPI command interface and implements two logical channels. Each channel has two banks, two 8-bit rows per bank, forced-refresh state, and an 8-bit accumulator. One lane-serial PIM datapath is shared between the channels.

Implemented operations are `ACT`, `PRE`, `WR`, `RD`, `REF`, `STATUS`, `ABORT`, `NOP`, experimental `ATTEND`, `DOT`, `MAC`, and accumulator byte reads. `DOT` and `MAC` use unsigned INT1 bit semantics or signed INT4 lane semantics and are computed through the shared lane-serial accumulator datapath. `ATTEND` consumes the accumulator score from a preceding `DOT`/`MAC` to perform a packed INT4 attention-value update. `CONFIG`, INT2/INT8 compute, and the generic `VADD` slot are reserved in this area-focused branch.
