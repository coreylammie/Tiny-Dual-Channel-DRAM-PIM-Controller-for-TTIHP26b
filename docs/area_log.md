# Area Log

| Stage | Storage | Features | Cells | Seq cells | Util. | WNS | Fits? | Notes |
|---|---|---|---:|---:|---:|---:|---|---|
| 0 | none | cloned blank repo | TBD | TBD | TBD | TBD | unknown | TTIHP26b template/hardening flow is not present in this repository yet. |
| 1 | none | SPI frontend, 32-bit framing | TBD | TBD | TBD | TBD | unknown | RTL implemented. Cocotb simulation blocked locally because `cocotb-config` is not installed. |
| 2 | 128b | dual-channel bank storage, ACT/PRE/WR/RD, refresh state | 1140 | 302 | TBD | TBD | synthesis-only | LibreLane/Yosys synthesis for `ihp-sg13g2` passed. Area 23697.2736, sequential area 14794.6176. Placement/routing not run yet. |
| 3 | 128b | minimal PU: VXOR, VADD, DOT, ACC | 3707 | 513 | TBD | TBD | synthesis-only, too large | LibreLane/Yosys synthesis passed lint-clean. Area 57155.3766, sequential area 25131.2544. Area growth is too high for a 1x1 target; next cut should serialize the accumulator bit path before adding more ops. |
| 3a | 128b | serial DOT accumulator: VXOR, VADD, DOT, ACC | 3021 | 445 | TBD | TBD | synthesis-only, needs more cuts | LibreLane/Yosys synthesis passed. Area 46827.6228, sequential area 21800.0160. Serial DOT saves 686 cells and 10327.7538 area versus Stage 3, at the cost of 144-cycle DOT latency. |
| 3b | 64b | 2 rows/bank fallback, serial DOT accumulator | 2577 synth / 3540 routed | 377 | 60.5% routed | setup WNS 0.0 typ | standalone routed, TT signoff pending | LibreLane/Yosys synthesis passed lint-clean. Detailed route reached 0 route DRC errors and 0 antenna violations under generic fallback SDC. |
| 3b-refresh255 | 64b | 255-cycle refresh cadence for SPI-safe smoke tests | 2588 | 381 | TBD | TBD | synthesis-only | Cocotb SPI tests pass locally with arm64 Python/Icarus. LibreLane/Yosys synthesis passed lint-clean. Area 39657.3786, sequential area 18664.7328. |
| 3b-queue | 64b | one pending command slot/channel while PIM busy | 2943 synth / 4074 routed | 429 | 61.4% routed | setup WNS 0.0 | standalone routed, TT signoff pending | Cocotb SPI tests pass locally. LibreLane/Yosys synthesis and local KLayout/Magic DRC passed with 0 route/Magic/KLayout DRC errors and 0 antenna violations under generic fallback SDC. |
| 3b-4rows | 128b | restored 4 rows/bank plus one pending command slot/channel | 3518 synth / 4774 routed | 497 | 59.9% routed | setup WNS 0.0 | standalone routed, TT signoff pending | Cocotb SPI tests pass locally. LibreLane/Yosys synthesis and local KLayout/Magic DRC passed with 0 route/Magic/KLayout DRC errors and 0 antenna violations under generic fallback SDC. |
| 3b-mac | 128b | MAC plus DOT INT1 RTL correction | 3503 synth / 4788 routed | 497 | 60.1% routed | setup WNS 0.0 | standalone routed, TT signoff pending | Cocotb now checks DOT and MAC accumulator values through SPI. Local KLayout/Magic DRC passed with 0 route/Magic/KLayout DRC errors and 0 antenna violations under generic fallback SDC. |
| 3b-config-refresh | 128b | configurable per-channel refresh reload | 3636 synth / 4983 routed | 513 | 60.8% routed | setup WNS 0.0 | standalone routed, TT signoff pending | Model and cocotb tests pass locally. Local KLayout/Magic DRC passed with 0 route/Magic/KLayout DRC errors and 0 antenna violations under generic fallback SDC. |
| 3b-stream-ops | 128b | STREAM.DOT/MAC plus VAND/VOR/VSUB/SUM/POPCNT/XNORDOT | 4970 synth / 6517 routed | 543 | 58.1% routed | setup WNS 0.0 | standalone routed, TT signoff pending | Model and cocotb tests pass locally, including a 4-row stream. Local KLayout/Magic DRC passed with 0 route/Magic/KLayout DRC errors and 0 antenna violations under generic fallback SDC. |
| 3b-parallel-dot-exp | 128b | experimental one-cycle parallel DOT/MAC/STREAM datapath | 16880 | 483 | N/A | N/A | rejected at synthesis | Model and cocotb behavior passed, but mapped area rose to 193566.8826 and synthesis check errors rose to 618. Not pursued to PnR. |
| 3b-lane-dot | 128b | lane-serial DOT/MAC/STREAM datapath compromise | 5441 synth / 6903 routed | 525 | 56.7% routed | setup WNS 0.0 | standalone routed, TT signoff pending | Model and cocotb behavior pass locally. Route/Magic/KLayout DRC passed with 0 errors and 0 antenna violations under generic fallback SDC. |
| 3b-config-control | 128b | config readback plus auto-refresh enable control | 5495 synth / 6926 routed | 527 | 56.1% routed | setup WNS 0.0 | standalone routed, TT signoff pending | Model and cocotb behavior pass locally. Route/Magic/KLayout DRC passed with 0 errors and 0 antenna violations under generic fallback SDC. |

## Local Check Log

| Date | Command | Result |
|---|---|---|
| 2026-08-31 | `python -m pytest test/test_model.py` | PASS, 5 tests |
| 2026-08-31 | `make` | BLOCKED, `cocotb-config` not found |
| 2026-08-31 | `scripts/synth.sh` | BLOCKED, `tt_tool.py` not found |
| 2026-08-31 | `scripts/synth.sh` | PASS through `Yosys.Synthesis` after adding standalone LibreLane config. 1 lint warning remains for an unused Stage 2 uop bit. |
| 2026-08-31 | `RUN_TAG=stage3-min-pu-synth scripts/synth.sh` | PASS through `Yosys.Synthesis` for minimal PU. 3707 cells, area 57155.3766, 0 lint warnings. |
| 2026-08-31 | `RUN_TAG=stage3-serial-acc-synth scripts/synth.sh` | PASS through `Yosys.Synthesis` for serial DOT accumulator. 3021 cells, area 46827.6228, 0 lint warnings. |
| 2026-08-31 | `RUN_TAG=stage3-serial-acc-no-row-reset-synth scripts/synth.sh` | PASS through `Yosys.Synthesis`, but rejected. Removing row reset increased area to 51281.6724 due to tie-cell growth. |
| 2026-08-31 | `python -m pytest test/test_model.py` | PASS, 12 tests |
| 2026-08-31 | `RUN_TAG=stage3b-64b-synth scripts/synth.sh` | PASS through `Yosys.Synthesis` for 64-bit fallback. 2577 cells, area 39374.2566, 0 lint warnings. |
| 2026-08-31 | `TO_STEP=OpenROAD.GlobalPlacement RUN_TAG=stage3b-64b-gpl scripts/synth.sh` | PASS through global placement. Final weighted congestion 0.7181, total routing overflow 0.0000. |
| 2026-08-31 | `TO_STEP=OpenROAD.DetailedRouting RUN_TAG=stage3b-64b-route scripts/synth.sh` | PASS through detailed routing. Route DRC errors 0, antenna violations 0, routed area 52742.8, utilization 60.5%. Uses generic fallback SDC, so TinyTapeout signoff remains open. |
| 2026-08-31 | TinyTapeout IHP template integration | Added `src/config.json`, `docs/info.md`, CI workflows, and `test/Makefile` for `TinyTapeout/tt-gds-action@ttihp26b`. Local cocotb remains blocked until cocotb is installed. |
| 2026-09-01 | `TO_STEP=KLayout.DRC RUN_TAG=stage3b-64b-klayout-drc scripts/synth.sh` | PASS locally. Magic DRC errors 0, KLayout DRC errors 0, route DRC errors 0, antenna violations 0, setup/hold WNS 0 under generic fallback SDC. |
| 2026-09-01 | GitHub Actions smoke workflow | BLOCKED before job creation. A minimal `echo ok` workflow also ended `startup_failure`, confirming the current blocker is repository/account Actions startup rather than TinyTapeout workflow content. |
| 2026-09-01 | `python -m pytest test/test_model.py` | PASS, 12 tests with 255-cycle refresh model. |
| 2026-09-01 | `make` | PASS, cocotb SPI direct-DUT tests: 3 pass, 0 fail. Requires arm64 Python/cocotb when using Homebrew arm64 Icarus on macOS. |
| 2026-09-01 | `make -C test` | PASS, TinyTapeout wrapper cocotb tests: 3 pass, 0 fail. |
| 2026-09-01 | `RUN_TAG=stage3b-refresh255-synth scripts/synth.sh` | PASS through `Yosys.Synthesis`. 2588 cells, area 39657.3786, 0 lint warnings. |
| 2026-09-01 | `TO_STEP=KLayout.DRC RUN_TAG=stage3b-refresh255-klayout-drc scripts/synth.sh` | PASS locally. Magic DRC errors 0, KLayout DRC errors 0, route DRC errors 0, antenna violations 0, setup/hold WNS 0 under generic fallback SDC. |
| 2026-09-02 | `python -m pytest test/test_model.py` | PASS, 12 tests. |
| 2026-09-02 | `make` | PASS, cocotb SPI direct-DUT tests: 4 pass, 0 fail. |
| 2026-09-02 | `make -C test` | PASS, TinyTapeout wrapper cocotb tests: 4 pass, 0 fail. |
| 2026-09-02 | `RUN_TAG=stage3b-queue-synth scripts/synth.sh` | PASS through `Yosys.Synthesis`. 2943 cells, area 45261.9090, sequential cells 429, sequential area 21016.1952, 0 lint warnings. |
| 2026-09-02 | `TO_STEP=KLayout.DRC RUN_TAG=stage3b-queue-klayout-drc scripts/synth.sh` | PASS locally. Magic DRC errors 0, KLayout DRC errors 0, route DRC errors 0, antenna violations 0, setup/hold WNS 0 under generic fallback SDC. Routed standard-cell utilization 61.4%. |
| 2026-09-02 | `python -m pytest test/test_model.py` | PASS, 12 tests with four rows per bank. |
| 2026-09-02 | `make` | PASS, cocotb SPI direct-DUT tests: 4 pass, 0 fail, including row 3 access. |
| 2026-09-02 | `make -C test` | PASS, TinyTapeout wrapper cocotb tests: 4 pass, 0 fail, including row 3 access. |
| 2026-09-02 | `RUN_TAG=stage3b-4rows-synth scripts/synth.sh` | PASS through `Yosys.Synthesis`. 3518 cells, area 52497.5472, sequential cells 497, sequential area 24347.4336, 0 lint warnings. |
| 2026-09-02 | `TO_STEP=KLayout.DRC RUN_TAG=stage3b-4rows-klayout-drc scripts/synth.sh` | PASS locally. Magic DRC errors 0, KLayout DRC errors 0, route DRC errors 0, antenna violations 0, setup/hold WNS 0 under generic fallback SDC. Routed standard-cell utilization 59.9%. |
| 2026-09-02 | `python -m pytest test/test_model.py` | PASS, 13 tests with MAC coverage. |
| 2026-09-02 | `make` | PASS, cocotb SPI direct-DUT tests: 5 pass, 0 fail, including DOT/MAC accumulator reads. |
| 2026-09-02 | `make -C test` | PASS, TinyTapeout wrapper cocotb tests: 5 pass, 0 fail, including DOT/MAC accumulator reads. |
| 2026-09-02 | `RUN_TAG=stage3b-mac-synth scripts/synth.sh` | PASS through `Yosys.Synthesis`. 3503 cells, area 52451.3178, sequential cells 497, sequential area 24347.4336, 0 lint warnings. |
| 2026-09-02 | `TO_STEP=KLayout.DRC RUN_TAG=stage3b-mac-klayout-drc scripts/synth.sh` | PASS locally. Magic DRC errors 0, KLayout DRC errors 0, route DRC errors 0, antenna violations 0, setup/hold WNS 0 under generic fallback SDC. Routed standard-cell utilization 60.1%. |
| 2026-09-02 | `python -m pytest test/test_model.py` | PASS, 14 tests with configurable refresh coverage. |
| 2026-09-02 | `make` | PASS, cocotb SPI direct-DUT tests: 6 pass, 0 fail, including configurable refresh status. |
| 2026-09-02 | `make -C test` | PASS, TinyTapeout wrapper cocotb tests: 6 pass, 0 fail, including configurable refresh status. |
| 2026-09-02 | `RUN_TAG=stage3b-config-refresh-synth scripts/synth.sh` | PASS through `Yosys.Synthesis`. 3636 cells, area 54177.4926, 0 lint warnings. |
| 2026-09-02 | `TO_STEP=KLayout.DRC RUN_TAG=stage3b-config-refresh-klayout-drc scripts/synth.sh` | PASS locally. Magic DRC errors 0, KLayout DRC errors 0, route DRC errors 0, antenna violations 0, setup/hold WNS 0 under generic fallback SDC. Routed standard-cell utilization 60.782%. |
| 2026-09-02 | `python -m pytest test/test_model.py` | PASS, 18 tests with stream and additional op coverage. |
| 2026-09-02 | `make` | PASS, cocotb SPI direct-DUT tests: 7 pass, 0 fail, including a 4-row stream and additional PIM ops. |
| 2026-09-02 | `make` from `test/` | PASS, TinyTapeout wrapper cocotb tests: 7 pass, 0 fail, including a 4-row stream and additional PIM ops. |
| 2026-09-02 | `RUN_TAG=stage3b-stream-ops-synth scripts/synth.sh` | PASS through `Yosys.Synthesis`. 4970 cells, area 70350.9030, sequential cells 543, sequential area 26600.9184, 0 lint warnings. |
| 2026-09-02 | `TO_STEP=KLayout.DRC RUN_TAG=stage3b-stream-ops-klayout-drc scripts/synth.sh` | PASS locally. Magic DRC errors 0, KLayout DRC errors 0, route DRC errors 0, antenna violations 0, setup/hold WNS 0 under generic fallback SDC. Routed standard-cell utilization 58.0557%. |
| 2026-09-02 | Parallel DOT/MAC/STREAM RTL experiment | PASS behaviorally: model tests 18 pass, direct-DUT cocotb 7 pass, wrapper cocotb 7 pass. |
| 2026-09-02 | `RUN_TAG=stage3b-parallel-dot-synth scripts/synth.sh` | REJECTED after synthesis. Lint errors 0, lint warnings 0, inferred latches 0, unmapped cells 0, but area was 193566.8826 across 16880 cells and synthesis check errors were 618. |
| 2026-09-02 | Lane-serial DOT/MAC/STREAM RTL experiment | PASS behaviorally: model tests 18 pass, direct-DUT cocotb 7 pass, wrapper cocotb 7 pass. |
| 2026-09-02 | `RUN_TAG=stage3b-lane-dot-synth scripts/synth.sh` | PASS through `Yosys.Synthesis`. 5441 cells, area 74602.6470, sequential cells 525, sequential area 25719.1200, 0 lint warnings, 0 synthesis check errors. |
| 2026-09-02 | `TO_STEP=KLayout.DRC RUN_TAG=stage3b-lane-dot-klayout-drc scripts/synth.sh` plus resume from `Odb.RemoveRoutingObstructions` | PASS locally. Initial full run hit a LibreLane detailed-routing DRC parser edge case after route convergence, then resumed through KLayout DRC from the routed state. Magic DRC errors 0, KLayout DRC errors 0, route DRC errors 0, antenna violations 0, setup/hold WNS 0 under generic fallback SDC. Routed standard-cell utilization 56.7019%. |
| 2026-09-02 | `python -m pytest test/test_model.py` | PASS, 19 tests with config readback and auto-refresh enable coverage. |
| 2026-09-02 | `make` | PASS, cocotb SPI direct-DUT tests: 7 pass, 0 fail, including config readback and auto-refresh enable coverage. |
| 2026-09-02 | `make` from `test/` | PASS, TinyTapeout wrapper cocotb tests: 7 pass, 0 fail, including config readback and auto-refresh enable coverage. |
| 2026-09-02 | `RUN_TAG=stage3b-config-control-synth scripts/synth.sh` | PASS through `Yosys.Synthesis`. 5495 cells, area 75687.2046, sequential cells 527, sequential area 25817.0976, 0 lint warnings, 0 synthesis check errors. |
| 2026-09-02 | `TO_STEP=KLayout.DRC RUN_TAG=stage3b-config-control-klayout-drc scripts/synth.sh` | PASS locally. Magic DRC errors 0, KLayout DRC errors 0, route DRC errors 0, antenna violations 0, setup/hold WNS 0 under generic fallback SDC. Routed standard-cell utilization 56.1497%. |
| 2026-09-04 | `python -m pytest test/test_model.py test/test_dense_layer_demo.py` | PASS, 23 model/example tests including dense-layer mixed-precision simulation. |
| 2026-09-04 | `make` and `make` from `test/` | PASS, 8 cocotb RTL tests in both direct-DUT and TinyTapeout-wrapper entry points, including dense-layer mixed-precision `STREAM.DOT`. |
| 2026-09-04 | `scripts/run_tests.sh` | PASS, 23 model/example tests and 11 TinyTapeout-wrapper cocotb RTL tests. Added sticky-error/abort, signed INT4 stream MAC, and queue-overflow coverage. |
| 2026-09-05 | GitHub Actions `gds` on official TT IHP `1x1` template | FAIL at global placement: standard-cell demand was about 85275.778 um^2 against a 28941.494 um^2 1x1 core, reported as 294.649% utilization. Updated `info.yaml` to `2x2` for the current feature set. |

## Stage 2 Synthesis Detail

- Flow: LibreLane Classic stopped at `Yosys.Synthesis`
- PDK: `ihp-sg13g2`
- Run tag: `stage2-memory-synth`
- Final mapped netlist: `runs/stage2-memory-synth/final/nl/tt_um_tiny_dram_pim.nl.v`
- Metrics file: `runs/stage2-memory-synth/final/metrics.json`
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 1
- Inferred latches: 0
- Unmapped cells: 0
- Synthesis check errors: 0
- Cells: 1140
- Sequential cells: 302 `sg13g2_dfrbpq_1`
- Total mapped area: 23697.2736
- Sequential area: 14794.6176

The 128-bit geometry can proceed to the minimal PU checkpoint for now, but this is not yet proof of 1x1 physical fit. The next hard gate should run floorplan, placement, STA, and routing with the final TinyTapeout IHP wrapper constraints.

## Stage 3 Minimal PU Detail

- Flow: LibreLane Classic stopped at `Yosys.Synthesis`
- PDK: `ihp-sg13g2`
- Run tag: `stage3-min-pu-synth`
- Implemented operations: `VXOR`, `VADD`, `DOT`, `ACC`
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 0
- Inferred latches: 0
- Unmapped cells: 0
- Synthesis check errors: 0
- Cells: 3707
- Sequential cells: 513 `sg13g2_dfrbpq_1`
- Total mapped area: 57155.3766
- Sequential area: 25131.2544

Review C decision: do not add more PU operations yet. The full-width accumulator/update path is too expensive. The next implementation step should convert DOT accumulation to a one-bit serial carry datapath and then rerun synthesis before adding `MAC`, `SUM`, `POPCNT`, `XNORDOT`, or `VSUB`.

## Stage 3a Serial DOT Accumulator Detail

- Flow: LibreLane Classic stopped at `Yosys.Synthesis`
- PDK: `ihp-sg13g2`
- Run tag: `stage3-serial-acc-synth`
- Implemented operations: `VXOR`, `VADD`, serial `DOT`, `ACC`
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 0
- Inferred latches: 0
- Unmapped cells: 0
- Synthesis check errors: 0
- Cells: 3021
- Sequential cells: 445 `sg13g2_dfrbpq_1`
- Total mapped area: 46827.6228
- Sequential area: 21800.0160

Review D decision: keep the row reset and serial DOT accumulator. The attempted no-row-reset variant increased mapped area to 51281.6724, so the next area reduction should come from reducing retained architectural state, such as row count or response/status state, rather than dropping reset coverage.

## Stage 3b 64-Bit Fallback Detail

- Flow: LibreLane Classic stopped at `Yosys.Synthesis`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-64b-synth`
- Storage geometry: 2 channels x 2 banks/channel x 2 rows/bank x 8 bits/row = 64 bits
- Implemented operations: `VXOR`, `VADD`, serial `DOT`, `ACC`
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 0
- Inferred latches: 0
- Unmapped cells: 0
- Synthesis check errors: 0
- Cells: 2577
- Sequential cells: 377 `sg13g2_dfrbpq_1`
- Total mapped area: 39374.2566
- Sequential area: 18468.7776

Review E decision: the 64-bit fallback is the current implementation target. The next hard gate should run deeper physical flow steps for floorplan, placement, routing, and STA before adding `STREAM` or more PU opcodes.

## Stage 3b Standalone Routing Detail

- Flow: LibreLane Classic stopped at `OpenROAD.DetailedRouting`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-64b-route`
- Die bbox: 307.34 um x 326.06 um
- Core area: 87178.3 um^2
- Routed standard-cell utilization: 60.5%
- Routed cells: 3540
- Routed cell area: 52742.8
- Hold repair buffers: 600
- Timing repair buffers: 902
- Global-route overflow: 0
- Detailed-route DRC errors: 0
- Antenna violating nets: 0
- Antenna violating pins: 0
- Route wirelength: 103698 um
- Route vias: 23146
- Typical setup WNS: 0.0
- Typical hold WNS: 0.0

This is a useful standalone physical checkpoint, not final TinyTapeout signoff. LibreLane used the generic fallback SDC because `PNR_SDC_FILE` and `SIGNOFF_SDC_FILE` are not present in this repository. The final integration step still needs the TinyTapeout IHP wrapper constraints and the full signoff flow.

## Stage 3b Local KLayout DRC Detail

- Flow: LibreLane Classic stopped at `KLayout.DRC`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-64b-klayout-drc`
- Magic DRC errors: 0
- KLayout DRC errors: 0
- Route DRC errors: 0
- Antenna violating nets: 0
- Antenna violating pins: 0
- Power-grid violations: 0
- Setup WNS: 0.0
- Hold WNS: 0.0
- Max slew violations: 0
- Max cap violations: 0
- Max fanout violations: 31
- Critical disconnected pins: 0
- XOR differences: 0

The remaining blockers are external to this local DRC checkpoint: GitHub Actions currently fails before creating any job even for a minimal smoke workflow, and final TinyTapeout signoff still needs the official submission/precheck environment to run successfully.

## Stage 3b Refresh255 Cocotb/Synthesis Detail

- Flow: cocotb RTL simulation plus LibreLane Classic stopped at `Yosys.Synthesis`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-refresh255-synth`
- Refresh cadence: automatic refresh every 255 core clocks per channel
- Reason for change: the prior 64-cycle cadence could collide with a conservative 32-bit SPI frame, setting sticky error during normal ACT/WR/RD smoke tests
- Cocotb direct-DUT tests: 3 pass, 0 fail
- Cocotb TinyTapeout wrapper tests: 3 pass, 0 fail
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 0
- Cells: 2588
- Sequential cells: 381 `sg13g2_dfrbpq_1`
- Total mapped area: 39657.3786
- Sequential area: 18664.7328

This checkpoint updates the behavioral test environment and refresh timing only. It does not replace the deeper routed/DRC result above; after this commit, the next physical checkpoint should rerun route/DRC on the 255-cycle refresh RTL.

## Stage 3b Refresh255 Local KLayout DRC Detail

- Flow: LibreLane Classic stopped at `KLayout.DRC`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-refresh255-klayout-drc`
- Magic DRC errors: 0
- KLayout DRC errors: 0
- Route DRC errors: 0
- Antenna violating nets: 0
- Antenna violating pins: 0
- Power-grid violations: 0
- Setup WNS: 0.0
- Hold WNS: 0.0
- Max slew violations: 0
- Max cap violations: 0
- Max fanout violations: 31
- Critical disconnected pins: 0
- XOR differences: 0
- Routed standard-cell instances: 3546
- Routed standard-cell area: 52889.8
- Final instance count including fill: 7844
- Final instance area including fill: 87461.3
- Route wirelength: 102424 um
- Route vias: 22902

This is the closest local replacement for the GitHub `gds` and `precheck` jobs, but it still uses the local LibreLane config and generic fallback SDC rather than the exact TinyTapeout GitHub Action wrapper.

## Stage 3b Queueing Cocotb/Synthesis Detail

- Flow: cocotb RTL simulation plus LibreLane Classic stopped at `Yosys.Synthesis`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-queue-synth`
- Feature change: one pending command slot per channel while the channel PIM datapath is busy
- Status visibility: status bit 0 reports a queued pending command
- Overflow behavior: a second command while the pending slot is occupied sets sticky error
- Cocotb direct-DUT tests: 4 pass, 0 fail
- Cocotb TinyTapeout wrapper tests: 4 pass, 0 fail
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 0
- Cells: 2943
- Sequential cells: 429 `sg13g2_dfrbpq_1`
- Total mapped area: 45261.9090
- Sequential area: 21016.1952

Compared with the `stage3b-refresh255-synth` baseline, queueing adds 355 mapped cells, 48 sequential cells, and 5604.5304 mapped area.

## Stage 3b Queueing Local KLayout DRC Detail

- Flow: LibreLane Classic stopped at `KLayout.DRC`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-queue-klayout-drc`
- Magic DRC errors: 0
- KLayout DRC errors: 0
- Route DRC errors: 0
- Antenna violating nets: 0
- Antenna violating pins: 0
- Power-grid violations: 0
- Setup WNS: 0.0
- Hold WNS: 0.0
- Max slew violations: 0
- Max cap violations: 0
- Max fanout violations: 35
- Critical disconnected pins: 0
- XOR differences: 0
- Routed standard-cell instances: 4074
- Routed standard-cell area: 60985.6
- Final instance count including fill: 8766
- Final instance area including fill: 99392.8
- Routed standard-cell utilization: 61.4%
- Route wirelength: 113806 um
- Route vias: 26136

This checkpoint is locally route-clean and DRC-clean under the same standalone LibreLane/generic-SDC caveat as the earlier local DRC runs. The next feature priority is restoring four rows per bank, then `MAC`, then configurable refresh timing. `STREAM` is below those priorities.

## Stage 3b Four-Row Cocotb/Synthesis Detail

- Flow: cocotb RTL simulation plus LibreLane Classic stopped at `Yosys.Synthesis`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-4rows-synth`
- Feature change: restored four 8-bit rows per bank
- Storage geometry: 2 channels x 2 banks/channel x 4 rows/bank x 8 bits/row = 128 bits
- Cocotb direct-DUT tests: 4 pass, 0 fail
- Cocotb TinyTapeout wrapper tests: 4 pass, 0 fail
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 0
- Cells: 3518
- Sequential cells: 497 `sg13g2_dfrbpq_1`
- Total mapped area: 52497.5472
- Sequential area: 24347.4336

Compared with the `stage3b-queue-synth` baseline, four-row storage adds 575 mapped cells, 68 sequential cells, and 7235.6382 mapped area.

## Stage 3b Four-Row Local KLayout DRC Detail

- Flow: LibreLane Classic stopped at `KLayout.DRC`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-4rows-klayout-drc`
- Magic DRC errors: 0
- KLayout DRC errors: 0
- Route DRC errors: 0
- Antenna violating nets: 0
- Antenna violating pins: 0
- Power-grid violations: 0
- Setup WNS: 0.0
- Hold WNS: 0.0
- Max slew violations: 0
- Max cap violations: 0
- Max fanout violations: 38
- Critical disconnected pins: 0
- XOR differences: 0
- Routed standard-cell instances: 4774
- Routed standard-cell area: 69551.4
- Final instance count including fill: 10463
- Final instance area including fill: 116103.0
- Die area: 131301 um^2
- Core area: 116103 um^2
- Routed standard-cell utilization: 59.9%
- Route wirelength: 137480 um
- Route vias: 31111

This checkpoint restores the original 128-bit storage target and is locally route-clean and DRC-clean under the standalone LibreLane/generic-SDC caveat. The next feature priority is `MAC`, then configurable refresh timing. `STREAM` remains below those priorities.

## Stage 3b MAC Cocotb/Synthesis Detail

- Flow: cocotb RTL simulation plus LibreLane Classic stopped at `Yosys.Synthesis`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-mac-synth`
- Feature change: added `REDUCE.MAC` as accumulator += dot product
- Correctness fix: INT1 DOT/MAC now add one per active bit-pair in the RTL serial datapath
- Cocotb direct-DUT tests: 5 pass, 0 fail
- Cocotb TinyTapeout wrapper tests: 5 pass, 0 fail
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 0
- Cells: 3503
- Sequential cells: 497 `sg13g2_dfrbpq_1`
- Total mapped area: 52451.3178
- Sequential area: 24347.4336

Compared with the `stage3b-4rows-synth` baseline, adding `MAC` and the DOT INT1 correction reduced mapped area by 46.2294 and 15 cells after synthesis optimization. Sequential cell count did not change.

## Stage 3b MAC Local KLayout DRC Detail

- Flow: LibreLane Classic stopped at `KLayout.DRC`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-mac-klayout-drc`
- Magic DRC errors: 0
- KLayout DRC errors: 0
- Route DRC errors: 0
- Antenna violating nets: 0
- Antenna violating pins: 0
- Power-grid violations: 0
- Setup WNS: 0.0
- Hold WNS: 0.0
- Max slew violations: 0
- Max cap violations: 0
- Max fanout violations: 39
- Critical disconnected pins: 0
- XOR differences: 0
- Routed standard-cell instances: 4788
- Routed standard-cell area: 69725.6
- Final instance count including fill: 10469
- Final instance area including fill: 116103.0
- Die area: 131188 um^2
- Core area: 116103 um^2
- Routed standard-cell utilization: 60.1%
- Route wirelength: 139111 um
- Route vias: 31283

This checkpoint is locally route-clean and DRC-clean under the standalone LibreLane/generic-SDC caveat. The next feature priority is configurable refresh timing. `STREAM` remains below that priority.

## Stage 3b Configurable Refresh Cocotb/Synthesis Detail

- Flow: cocotb RTL simulation plus LibreLane Classic stopped at `Yosys.Synthesis`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-config-refresh-synth`
- Feature change: added `CONFIG subopcode 0` to set per-channel automatic refresh reload from `imm8`
- Default refresh reload: 254, preserving the 255-core-clock reset interval
- Cocotb direct-DUT tests: 6 pass, 0 fail
- Cocotb TinyTapeout wrapper tests: 6 pass, 0 fail
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 0
- Cells: 3636
- Sequential cells: 513
- Total mapped area: 54177.4926

Compared with the `stage3b-mac-synth` baseline, configurable refresh adds 133 mapped cells and 1726.1748 mapped area.

## Stage 3b Configurable Refresh Local KLayout DRC Detail

- Flow: LibreLane Classic stopped at `KLayout.DRC`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-config-refresh-klayout-drc`
- Magic DRC errors: 0
- KLayout DRC errors: 0
- Route DRC errors: 0
- Antenna violating nets: 0
- Antenna violating pins: 0
- Power-grid violations: 0
- Setup WNS: 0.0
- Hold WNS: 0.0
- Max slew violations: 0
- Max cap violations: 0
- Max fanout violations: 42
- Critical disconnected pins: 0
- XOR differences: 0
- Routed standard-cell instances: 4983
- Routed standard-cell area: 72458.1
- Final instance count including fill: 10711
- Final instance area including fill: 119210.0
- Die area: 135255 um^2
- Core area: 119210 um^2
- Routed standard-cell utilization: 60.782%
- Route wirelength: 145478 um
- Route vias: 32629

This checkpoint is locally route-clean and DRC-clean under the standalone LibreLane/generic-SDC caveat.

## Stage 3b Stream/Ops Cocotb/Synthesis Detail

- Flow: cocotb RTL simulation plus LibreLane Classic stopped at `Yosys.Synthesis`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-stream-ops-synth`
- Feature change: added `STREAM.DOT`, `STREAM.MAC`, `VAND`, `VOR`, `VSUB`, `SUM`, `POPCNT`, and `XNORDOT`
- Stream count encoding: `imm8[2:0]`, valid counts 1 through 4
- Cocotb direct-DUT tests: 7 pass, 0 fail
- Cocotb TinyTapeout wrapper tests: 7 pass, 0 fail
- Model tests: 18 pass, 0 fail
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 0
- Inferred latches: 0
- Unmapped cells: 0
- Synthesis check errors: 0
- Cells: 4970
- Sequential cells: 543
- Total mapped area: 70350.9030
- Sequential area: 26600.9184

Compared with the `stage3b-config-refresh-synth` baseline, stream and the additional primitive operations add 1334 mapped cells, 30 sequential cells, and 16173.4104 mapped area.

## Stage 3b Stream/Ops Local KLayout DRC Detail

- Flow: LibreLane Classic stopped at `KLayout.DRC`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-stream-ops-klayout-drc`
- Magic DRC errors: 0
- KLayout DRC errors: 0
- Route DRC errors: 0
- Antenna violating nets: 0
- Antenna violating pins: 0
- Power-grid violations: 0
- Setup WNS: 0.0
- Hold WNS: 0.0
- Max slew violations: 0
- Max cap violations: 0
- Max fanout violations: 43
- Critical disconnected pins: 0
- XOR differences: 0
- Routed standard-cell instances: 6517
- Routed standard-cell area: 90159.4
- Final instance count including fill: 14745
- Final instance area including fill: 155298
- Die area: 173226 um^2
- Core area: 155298 um^2
- Routed standard-cell utilization: 58.0557%
- Route wirelength: 218630 um
- Route vias: 44025

This checkpoint is locally route-clean and DRC-clean under the standalone LibreLane/generic-SDC caveat. The design is using about 58.1% of the allocated standard-cell core area after routing, leaving about 41.9% core whitespace before any final TinyTapeout wrapper-specific changes.

## Stage 3b Parallel DOT/MAC Experiment Detail

- Flow: temporary RTL experiment plus cocotb and LibreLane Classic stopped at `Yosys.Synthesis`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-parallel-dot-synth`
- Feature experiment: replaced the 144-cycle bit-serial DOT/MAC datapath with a one-cycle combinational dot-product path and made STREAM advance one row pair per core cycle
- Public ISA change: none
- Model tests: 18 pass, 0 fail
- Cocotb direct-DUT tests: 7 pass, 0 fail
- Cocotb TinyTapeout wrapper tests: 7 pass, 0 fail
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 0
- Inferred latches: 0
- Unmapped cells: 0
- Synthesis check errors: 618
- Cells: 16880
- Sequential cells: 483
- Total mapped area: 193566.8826
- Sequential area: 23661.5904

Decision: reject the full parallel datapath. It cuts DOT/MAC latency from 144 cycles to 1 cycle and STREAM from `144 x count` to `count`, but it adds 11910 cells and 123215.9796 mapped area versus the serial stream/op checkpoint. That synthesis area is already larger than the prior routed core area, so PnR/DRC was not run for this temporary RTL.

## Stage 3b Lane-Serial DOT/MAC Detail

- Flow: cocotb RTL simulation plus LibreLane Classic stopped at `Yosys.Synthesis`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-lane-dot-synth`
- Feature change: replaced the 144-cycle one-bit serial DOT/MAC engine with a lane-serial engine
- INT1 DOT/MAC busy latency: 1 cycle
- INT2 DOT/MAC busy latency: 4 cycles
- INT4 DOT/MAC busy latency: 2 cycles
- INT8 DOT/MAC busy latency: 1 cycle
- STREAM latency: per-row DOT/MAC latency multiplied by `imm8[2:0]` row count
- Model tests: 18 pass
- Cocotb direct-DUT tests: 7 pass, 0 fail
- Cocotb TinyTapeout wrapper tests: 7 pass, 0 fail
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 0
- Inferred latches: 0
- Unmapped cells: 0
- Synthesis check errors: 0
- Cells: 5441
- Sequential cells: 525 `sg13g2_dfrbpq_1`
- Total mapped area: 74602.6470
- Sequential area: 25719.1200

Compared with the `stage3b-stream-ops-synth` baseline, the lane-serial compromise adds 471 mapped cells and 4251.7440 mapped area, while reducing sequential cells by 18.

## Stage 3b Lane-Serial DOT/MAC Local KLayout DRC Detail

- Flow: LibreLane Classic stopped at `KLayout.DRC`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-lane-dot-klayout-drc`
- LibreLane note: the first full run converged detailed routing to 0 DRC errors, then hit a DRC report parser edge case because it attempted to parse an empty XML DRC database as OpenROAD text. The flow was resumed from `Odb.RemoveRoutingObstructions` using the routed state and completed through KLayout DRC.
- Magic DRC errors: 0
- KLayout DRC errors: 0
- Route DRC errors: 0
- Antenna violating nets: 0
- Antenna violating pins: 0
- Power-grid violations: 0
- Setup WNS: 0.0
- Hold WNS: 0.0
- Max slew violations: 0
- Max cap violations: 0
- Max fanout violations: 43
- Critical disconnected pins: 0
- XOR differences: 0
- Routed standard-cell instances: 6903
- Routed standard-cell area: 93349.1
- Final instance count including fill: 15717
- Final instance area including fill: 164631
- Die area: 183169 um^2
- Core area: 164631 um^2
- Routed standard-cell utilization: 56.7019%
- Route wirelength: 217772 um
- Route vias: 45788

Decision: keep the lane-serial compromise. It does not reach one-cycle DOT/MAC for every precision, but it gives one-cycle INT1/INT8, two-cycle INT4, four-cycle INT2, and route-clean signoff locally. The full one-cycle parallel datapath remains rejected.

## Stage 3b Config Control Detail

- Flow: cocotb RTL simulation plus LibreLane Classic stopped at `Yosys.Synthesis`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-config-control-synth`
- Feature change: added `CONFIG` subops for refresh reload readback and automatic refresh enable control
- `CONFIG.0`: write refresh reload from `imm8`
- `CONFIG.1`: read refresh reload
- `CONFIG.2`: write automatic refresh enable from `imm8[0]`
- `CONFIG.3`: read automatic refresh enable
- Model tests: 19 pass
- Cocotb direct-DUT tests: 7 pass, 0 fail
- Cocotb TinyTapeout wrapper tests: 7 pass, 0 fail
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 0
- Inferred latches: 0
- Unmapped cells: 0
- Synthesis check errors: 0
- Cells: 5495
- Sequential cells: 527 `sg13g2_dfrbpq_1`
- Total mapped area: 75687.2046
- Sequential area: 25817.0976

Compared with the `stage3b-lane-dot-synth` baseline, config control adds 54 mapped cells, 2 sequential cells, and 1084.5576 mapped area.

## Stage 3b Config Control Local KLayout DRC Detail

- Flow: LibreLane Classic stopped at `KLayout.DRC`
- PDK: `ihp-sg13g2`
- Run tag: `stage3b-config-control-klayout-drc`
- Magic DRC errors: 0
- KLayout DRC errors: 0
- Route DRC errors: 0
- Antenna violating nets: 0
- Antenna violating pins: 0
- Power-grid violations: 0
- Setup WNS: 0.0
- Hold WNS: 0.0
- Max slew violations: 0
- Max cap violations: 0
- Max fanout violations: 40
- Critical disconnected pins: 0
- XOR differences: 0
- Routed standard-cell instances: 6926
- Routed standard-cell area: 93964.1
- Final instance count including fill: 16031
- Final instance area including fill: 167346
- Die area: 185704 um^2
- Core area: 167346 um^2
- Routed standard-cell utilization: 56.1497%
- Route wirelength: 232922 um
- Route vias: 46810

Decision: keep the config control subops. They are low-cost, useful for software bring-up, and remain locally route-clean and DRC-clean under the standalone LibreLane/generic-SDC caveat.

## Dense-Layer Test Cleanup Detail

- Flow: model/example pytest plus cocotb RTL simulation
- Feature change: no RTL change; added dense-layer model example and dense-layer cocotb regression
- Mixed-precision behavior: activation and weight precision are declared independently in the software helper; the hardware command executes at the wider precision because the RTL exposes one precision field per DOT/STREAM command
- Model/example tests: 23 pass, 0 fail
- Cocotb TinyTapeout-wrapper tests: 11 pass, 0 fail
- Physical status: unchanged from `stage3b-config-control-klayout-drc`

The cleanup before public Actions keeps `docs/isa.md` as the canonical ISA document, shortens the README, adds `docs/status.md`, and updates CI/local test scripts to include the dense-layer Python regression.

## 1x1 Target, 2 Rows Per Bank Detail

- Date: 2026-09-05
- Branch: `1x1-target`
- Flow: model/example pytest, cocotb RTL simulation, and LibreLane Classic stopped at `Yosys.Synthesis`
- Feature change: reduced each bank from four 8-bit rows to two 8-bit rows while preserving two channels and two banks per channel
- Official TinyTapeout tile setting: `1x1`
- Storage geometry: 2 channels x 2 banks/channel x 2 rows/bank x 8 bits/row = 64 bits
- Model/example tests: 23 pass, 0 fail
- Cocotb TinyTapeout-wrapper RTL tests: 11 pass, 0 fail
- Lint errors: 0
- Lint timing construct errors: 0
- Lint warnings: 0
- Cells: 4815
- Sequential cells: 455 `sg13g2_dfrbpq_1`
- Total mapped area: 65116.0566
- Sequential area: 22289.9040

Decision: two rows per bank is a clean first reduction and preserves the desired 2-channel, 2-bank framing, but it is unlikely to fit the official 1x1 TinyTapeout IHP wrapper by itself. The previous official 1x1 run had a 28941.494 um^2 core area; this synthesis checkpoint is still about 2.25x that area before placement overhead.

## 1x1 Target Official GDS Attempt

- Date: 2026-09-05
- Branch: `1x1-target`
- Commit: `b5bf3d8`
- GitHub Actions `test`: pass
- GitHub Actions `gds`: fail at `OpenROAD.GlobalPlacement`
- Official core area: 28941.494 um^2
- Floorplan total instances area: 64692.432 um^2
- GPL movable instances area after pin-density adjustment: 74320.634 um^2
- GPL utilization: 256.796%
- Failure: `[GPL-0301] Utilization 256.796 % exceeds 100%.`

Decision: layout tuning is not enough for the current reduced-depth RTL. To fit a 1x1 coupon while preserving two channels and two banks per channel, the next experiment needs to remove or substantially simplify logic, not just shrink row storage. Likely cuts are STREAM control, secondary vector/reduction operations, command queueing, or configurable refresh state.

## 1x1 Target Without Autonomous Row-Walk

- Date: 2026-09-05
- Branch: `1x1-target`
- Feature change: removed the autonomous `STREAM.DOT`/`STREAM.MAC` control path and reserved opcode `0x7`
- Preserved geometry: 2 channels x 2 banks/channel x 2 rows/bank x 8 bits/row
- Preserved PIM operations: `VXOR`, `VAND`, `VOR`, `VADD`, `VSUB`, `DOT`, `MAC`, `SUM`, `POPCNT`, `XNORDOT`, and accumulator byte reads
- Host impact: multi-row dot products now use explicit `ACT` plus `DOT`/`MAC` commands per row pair
- Local model/example tests: 24 pass, 0 fail
- Local cocotb TinyTapeout-wrapper RTL tests: 11 pass, 0 fail
- Run tag: `1x1-2rows-no-stream-synth`
- Synthesis result: pass through `Yosys.Synthesis`
- Lint: 0 errors, 0 warnings
- Cells: 4102
- Sequential cells: 429 `sg13g2_dfrbpq_1`
- Total mapped area: 56587.9608
- Sequential area: 21016.1952

Compared with the prior 2-row branch checkpoint, removing autonomous row-walk control saves 713 mapped cells and 8528.0958 mapped area. The synthesis area is still about 1.96x the official 28941.494 um^2 1x1 core area before placement overhead, so the next hard check is the official TinyTapeout GDS flow on this branch.

## 1x1 Target Without Autonomous Row-Walk Official GDS Attempt

- Date: 2026-09-05
- Branch: `1x1-target`
- Commit: `245d3bc`
- GitHub Actions `test`: pass
- GitHub Actions `gds`: fail at `OpenROAD.GlobalPlacement`
- Official core area: 28941.494 um^2
- Floorplan total instances area: 56400.624 um^2
- GPL movable instances area after pin-density adjustment: 64113.250 um^2
- GPL utilization: 221.527%
- Failure: `[GPL-0301] Utilization 221.527 % exceeds 100%.`

Decision: removing autonomous row-walk control helps materially but is not enough for a 1x1 coupon while preserving two channels and two banks per channel. The next experiment needs another functional simplification, with the largest remaining candidates being secondary vector/reduction operations, command queueing, configurable refresh state, or the width/precision of the accumulator datapath.

## 1x1 Target RTL Slimming

- Date: 2026-09-05
- Branch: `1x1-target`
- Feature change: preserved the no-STREAM ISA but narrowed internal queued command state, reduced the PIM busy counter from 8 bits to 4 bits, and replaced the retained active opcode with a one-bit VOP/REDUCE state
- Local model/example tests: 24 pass, 0 fail
- Local cocotb TinyTapeout-wrapper RTL tests: 11 pass, 0 fail
- Run tag: `1x1-2rows-no-stream-rtl-slim-synth`
- Synthesis result: pass through `Yosys.Synthesis`
- Lint: 0 errors, 0 warnings
- Cells: 4127
- Sequential cells: 419 `sg13g2_dfrbpq_1`
- Total mapped area: 56234.3796
- Sequential area: 20526.3072

Compared with the no-STREAM baseline, this saves 353.5812 mapped area and 10 sequential cells, but increases total cell count by 25 due to changed combinational mapping. A more aggressive same-ISA experiment that made VOP write back immediately was rejected because it worsened mapped area to 56977.7544 despite reducing sequential cells.

Decision: straightforward RTL cleanup is not enough to make 1x1 viable. The remaining gap is still roughly 56234.3796 / 28941.494 = 1.94x before placement overhead, so the next useful experiments need architectural simplification rather than placement-only tuning or small coding-style changes.
