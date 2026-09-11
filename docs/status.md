# Current Status

This file is the short public-facing status snapshot. The detailed historical area and decision log remains in `docs/area_log.md`.

## Functional State

- Geometry: 2 channels x 2 banks/channel x 2 rows/bank x 8 bits/row = 64 physical storage bits
- Interface: fixed 32-bit SPI command framing with next-frame responses
- Physical I/O: SPI is implemented on `ui_in[0]`, `ui_in[1]`, `ui_in[2]`, and `uo_out[0]`; remaining output pins are tied low
- Memory commands: `ACT`, `PRE`, `WR`, `RD`, `REF`, `STATUS`, `ABORT`, and `NOP`; `CONFIG` is reserved
- PIM operations: experimental `ATTEND`, `DOT`, `MAC`, and 8-bit `ACC`; one shared PU is multiplexed between both channels, while INT2/INT8 compute and the generic `VADD` slot are reserved for area
- Refresh: explicit host-issued `REF` with refresh-busy bank blocking; autonomous refresh is reserved for area
- Busy handling: PIM commands issued while the shared PU is busy set sticky error and are dropped

## Local Verification

- Python model/example tests: 26 pass, 0 fail
- Cocotb TinyTapeout-wrapper RTL tests from `test/`: 11 pass, 0 fail
- Latest local synthesis checkpoint: 1514 cells, total mapped area 25579.1844, lint-clean on this experimental branch
- Latest official TinyTapeout `1x1` GDS check: failed detailed placement at 99.622% utilization before reserving INT2 compute
- Latest local route/DRC checkpoint: not yet run for this no-STREAM branch
- Routed standard-cell utilization: not yet measured for this no-STREAM branch
- Official TinyTapeout tile setting: `1x1` on the reduced-depth target branch

## Remaining External Check

Final TinyTapeout confidence still requires a smaller RTL configuration that passes the official GitHub Actions GDS flow:

- `test` workflow for Ubuntu cocotb regression
- `gds` workflow for TinyTapeout GDS build, precheck, gate-level test, and viewer generation
