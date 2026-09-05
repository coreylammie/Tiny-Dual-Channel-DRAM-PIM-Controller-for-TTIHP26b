# Tiny Dual-Channel DRAM-PIM Controller for TTIHP26b

This project asks a deliberately small question: how much of a DRAM processing-in-memory controller can fit in a tiny TinyTapeout IHP standard-cell macro?

The result is a tiny dual-channel DRAM-PIM controller with real memory-control behavior, refresh state, command queueing, and cross-bank compute. It is not a density-competitive DRAM macro. It is a silicon-testable controller architecture for near-memory operations under an extreme area budget. The useful idea is the compromise: keep the ISA expressive enough for row moves, status/debug, low-precision vector operations, dot products, MACs, and short row streams, but serialize the expensive arithmetic lanes enough that the design still routes locally.

## High-Level Design

- **Host interface:** a 32-bit SPI command frame enters through the TinyTapeout `ui_in`/`uo_out` pins. Responses are returned on the following SPI frame with status and read data.
- **Two independent channels:** each channel has its own control state, refresh timing, sticky error bit, pending command slot, bank pair, and accumulator.
- **Banked row store:** each channel contains two banks with four 8-bit rows per bank. `ACT`, `PRE`, `WR`, and `RD` expose a DRAM-like open-row programming model.
- **Near-bank processing unit:** the PU operates across the selected rows in the two banks. It supports bitwise vector ops, lane-wise add/subtract, lane sums, dot products, MAC, popcount, XNOR-dot, and short row streams.
- **Variable compute resolution:** each compute command selects how an 8-bit row is interpreted: eight INT1 lanes, four signed INT2 lanes, two signed INT4 lanes, or one signed INT8 lane.
- **Row streaming:** `STREAM.DOT` and `STREAM.MAC` walk up to four consecutive row pairs and accumulate results without requiring one host command per row.

The implementation keeps the visible ISA relatively expressive, but uses a lane-serial DOT/MAC datapath so the design remains small enough to route in the TinyTapeout IHP area budget.

## Quick Start

Run fast model and example tests:

```sh
python -m pytest test/test_model.py test/test_dense_layer_demo.py
```

Run a dense-layer inference demo against the controller model:

```sh
python examples/dense_layer_demo.py
```

The demo uses `STREAM.DOT` to compute quantized dense-layer outputs and compares the result with a pure Python reference. Activation and weight precision can be configured independently; mixed-precision layers are executed at the wider lane precision, which preserves arithmetic while reducing packing density to the wider operand's lane count.

Run cocotb RTL tests when cocotb and a simulator are installed:

```sh
cd test
make
```

The TinyTapeout CI flow runs the cocotb harness from `test/Makefile`.

Attempt local TinyTapeout hardening:

```sh
scripts/synth.sh
```

The synthesis script uses LibreLane through Nix. By default it runs the current checkpoint through `Yosys.Synthesis` for `ihp-sg13g2`:

```sh
LIBRELANE_ROOT=/Users/coreylammie/librelane scripts/synth.sh
```

Set `TO_STEP` to continue further through the LibreLane classic flow.

Current verification checkpoint:

- Implements `VXOR`, `VAND`, `VOR`, `VADD`, `VSUB`, `DOT`, `MAC`, `SUM`, `POPCNT`, `XNORDOT`, `STREAM.DOT`, `STREAM.MAC`, and `ACC`
- Adds one pending command slot per channel for commands issued while `PIM busy` is high
- Restores all four encoded row values per bank
- Adds `CONFIG` subops to set/read each channel's automatic refresh reload counter and enable/disable automatic refresh
- `STREAM` uses `imm8[2:0]` as a row-pair count from 1 through 4 and runs lane-serial DOT/MAC over consecutive row pairs
- Model/example tests: 23 passing
- Cocotb SPI RTL tests: 11 TinyTapeout-wrapper tests passing
- Synthesis: 5495 cells, total mapped area 75687.2046
- Official TinyTapeout area target: `2x2` tiles for the current feature set
- Local KLayout/Magic DRC: 0 route DRC errors, 0 Magic DRC errors, 0 KLayout DRC errors, and 0 antenna violations under generic fallback SDC
- Routed standard-cell utilization: 56.1497%
- Decision: the lane-serial DOT/MAC compromise is locally routed/DRC-clean under the standalone LibreLane/generic-SDC caveat.

## Documentation

The canonical ISA reference is [docs/isa.md](docs/isa.md). Physical bring-up notes are in [docs/bringup.md](docs/bringup.md). Supporting architecture, timing, and physical checkpoint notes are in [docs/architecture.md](docs/architecture.md), [docs/timing.md](docs/timing.md), and [docs/area_log.md](docs/area_log.md).

## License

This project is released under the MIT License.
