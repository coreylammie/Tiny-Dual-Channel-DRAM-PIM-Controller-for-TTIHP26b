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
- Latest official TinyTapeout `1x1` GDS check: pass, including GDS build, precheck, gate-level test, and viewer generation
- Latest route/DRC checkpoint: official TinyTapeout GDS build reports route DRC 0, Magic DRC 0, LVS 0, antenna violations 0, setup violations 0, and hold violations 0
- Routed standard-cell utilization: 95.304% in the official TinyTapeout GDS build
- Official TinyTapeout tile setting: `1x1` on the reduced-depth target branch

## Remaining External Check

Final TinyTapeout confidence now depends on manual review of the generated artifacts and any shuttle-specific submission checks outside this repository:

- `test` workflow for Ubuntu cocotb regression passed on the final branch commit
- `gds` workflow for TinyTapeout GDS build, precheck, gate-level test, and viewer generation passed on the final branch commit
