# Tiny Dual-Channel DRAM-PIM Controller Architecture

This project is a standard-cell RTL implementation of a tiny dual-channel DRAM-PIM controller featuring shared lane-serial cross-bank compute, refresh-aware memory control, and independently addressable channels under an extreme silicon-area constraint.

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

Each channel owns a small forced-refresh state machine. `REF` starts a fixed four-cycle refresh on the selected bank, and accesses to the refreshing bank set sticky error. Autonomous refresh scheduling and `CONFIG` read/write state are reserved in this 1x1 fitting branch to reduce area.

Each channel owns an 8-bit accumulator, while both channels share one lane-serial arithmetic PU. If a PIM command arrives while the shared PU is busy, the command is dropped and sticky error is set. `ABORT` clears the selected channel's sticky error, refresh state, accumulator, and any active PIM operation owned by that channel.

The implemented PIM operations are experimental `ATTEND`, `DOT`, and `MAC`, plus accumulator byte reads. `ATTEND` reuses signed lane extraction and multiply-add logic to update the active output/state row in bank B from a value row in bank A and the low INT4 lane of the selected channel accumulator. `DOT` and `MAC` share a lane-serial accumulator datapath: INT1 uses an 8-bit popcount term, while INT4 adds one signed lane product per busy cycle. INT2/INT8 compute and the generic `VADD` slot are reserved in this area-focused branch. Multi-row dot products and attention updates are host-driven sequences of `ACT`, `DOT`/`MAC`, and `ATTEND`; opcode `0x7` and the remaining secondary PU subopcodes are reserved.

## TinyTapeout Pins

`ui_in[0]` is SPI SCLK, `ui_in[1]` is active-low CS, and `ui_in[2]` is MOSI. `uo_out[0]` is MISO. Remaining output bits are tied low; machine-readable status is available through `STATUS` commands.

## Physical Status

The current 1x1 branch passes the official TinyTapeout GDS workflow, including precheck, gate-level test, and viewer generation. The routed design reports 95.581% standard-cell utilization with route DRC 0, Magic DRC 0, LVS 0, antenna violations 0, setup violations 0, hold violations 0, max slew violations 0, and max cap violations 0.
