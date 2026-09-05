# Current Status

This file is the short public-facing status snapshot. The detailed historical area and decision log remains in `docs/area_log.md`.

## Functional State

- Geometry: 2 channels x 2 banks/channel x 2 rows/bank x 8 bits/row = 64 physical storage bits
- Interface: fixed 32-bit SPI command framing with next-frame responses
- Physical I/O: SPI is implemented on `ui_in[0]`, `ui_in[1]`, `ui_in[2]`, and `uo_out[0]`
- Memory commands: `ACT`, `PRE`, `WR`, `RD`, `REF`, `STATUS`, `CONFIG`, `ABORT`, and `NOP`
- PIM operations: `VXOR`, `VAND`, `VOR`, `VADD`, `VSUB`, `DOT`, `MAC`, `SUM`, `POPCNT`, `XNORDOT`, and `ACC`
- Refresh: per-channel automatic refresh with configurable reload and enable control
- Queueing: one pending command slot per channel while the PIM datapath is busy

## Local Verification

- Python model/example tests: 24 pass, 0 fail
- Cocotb TinyTapeout-wrapper RTL tests from `test/`: 11 pass, 0 fail
- Latest local synthesis checkpoint: 4102 cells, total mapped area 56587.9608, lint-clean
- Latest official TinyTapeout `1x1` GDS check: failed global placement at 221.527% utilization after removing autonomous row-walk control
- Latest local route/DRC checkpoint: not yet run for this no-STREAM branch
- Routed standard-cell utilization: not yet measured for this no-STREAM branch
- Official TinyTapeout tile setting: `1x1` on the reduced-depth target branch

## Remaining External Check

Final TinyTapeout confidence still requires a smaller RTL configuration that passes the official GitHub Actions flow:

- `test` workflow for Ubuntu cocotb regression
- `gds` workflow for TinyTapeout GDS build, precheck, gate-level test, and viewer generation
