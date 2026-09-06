# Tiny Dual-Channel DRAM-PIM Controller Architecture

This project is a standard-cell RTL implementation of a tiny dual-channel DRAM-PIM controller featuring lane-serial cross-bank compute, refresh-aware scheduling, and independently concurrent channels under an extreme silicon-area constraint.

## 64-Bit 1x1 Target Checkpoint

The current checkpoint implements the transport and memory-control foundation plus the first PU operations:

```text
SPI slave
  -> 32-bit command decoder
  -> channel select
     -> channel 0: 2 banks x 2 rows x 8 bits
     -> channel 1: 2 banks x 2 rows x 8 bits
```

Each bank stores two 8-bit rows, an open-row bit, and a two-bit active-row index. There is no duplicated row-buffer storage. `ACT` records the selected row, `WR` and `RD` target the currently active row, and `PRE` closes the bank.

Each channel owns independent refresh state. Channel 0 starts at refresh phase 0 and channel 1 starts at phase 32 to avoid synchronized refresh behavior. The automatic refresh period is fixed at 255 core clocks, and `CONFIG` can enable/disable autonomous refresh scheduling and read back that enable bit. Forced `REF` commands remain available when autonomous refresh is disabled.

Each channel also owns an 18-bit accumulator and a small atomic-operation busy counter. If a command arrives while the channel PIM datapath is busy, the command is dropped and sticky error is set. `ABORT` clears sticky error, refresh state, and any active PIM operation.

The implemented PIM operations are `VXOR`, `VADD`, `DOT`, and `MAC`, plus accumulator byte reads. `VXOR` and `VADD` are immediate row-transform commands. `DOT` and `MAC` share a lane-serial accumulator datapath: INT1 uses an 8-bit popcount term, while INT2/INT4 add one signed lane product per busy cycle. INT8 compute is reserved in this area-reduced branch. Multi-row dot products are host-driven sequences of `ACT`, `DOT`, and `MAC`; opcode `0x7` and the removed secondary PU subopcodes are reserved.

## TinyTapeout Pins

`ui_in[0]` is SPI SCLK, `ui_in[1]` is active-low CS, and `ui_in[2]` is MOSI. `uo_out[0]` is MISO. Remaining output bits expose compact debug status for open banks and refresh-busy state.

## Physical Status

The latest local LibreLane run is route-clean and DRC-clean under the standalone local config and generic fallback SDC. Final TinyTapeout signoff still needs the official submission/precheck environment.
