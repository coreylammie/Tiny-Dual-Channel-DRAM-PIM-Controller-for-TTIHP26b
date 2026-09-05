# Current Status

This file is the short public-facing status snapshot. The detailed historical area and decision log remains in `docs/area_log.md`.

## Functional State

- Geometry: 2 channels x 2 banks/channel x 4 rows/bank x 8 bits/row = 128 physical storage bits
- Interface: fixed 32-bit SPI command framing with next-frame responses
- Physical I/O: SPI is implemented on `ui_in[0]`, `ui_in[1]`, `ui_in[2]`, and `uo_out[0]`
- Memory commands: `ACT`, `PRE`, `WR`, `RD`, `REF`, `STATUS`, `CONFIG`, `ABORT`, and `NOP`
- PIM operations: `VXOR`, `VAND`, `VOR`, `VADD`, `VSUB`, `DOT`, `MAC`, `SUM`, `POPCNT`, `XNORDOT`, `STREAM.DOT`, `STREAM.MAC`, and `ACC`
- Refresh: per-channel automatic refresh with configurable reload and enable control
- Queueing: one pending command slot per channel while the PIM datapath is busy

## Local Verification

- Python model/example tests: 23 pass, 0 fail
- Cocotb TinyTapeout-wrapper RTL tests from `test/`: 11 pass, 0 fail
- Latest local synthesis checkpoint: 5495 cells, total mapped area 75687.2046
- Latest local route/DRC checkpoint: 0 route DRC errors, 0 Magic DRC errors, 0 KLayout DRC errors, 0 antenna violations
- Routed standard-cell utilization: 56.1497%
- Official TinyTapeout tile setting: `2x2`; the current feature set exceeds the `1x1` IHP template capacity

## Remaining External Check

Final TinyTapeout confidence still requires the official GitHub Actions flow to complete:

- `test` workflow for Ubuntu cocotb regression
- `gds` workflow for TinyTapeout GDS build, precheck, gate-level test, and viewer generation
