# Tiny Dual-Channel DRAM-PIM Controller for TTIHP26b

This project asks a deliberately small question: how much of a DRAM processing-in-memory controller can fit in a tiny TinyTapeout IHP standard-cell macro?

The result is a tiny dual-channel DRAM-PIM controller with real memory-control behavior, refresh state, command queueing, and cross-bank compute. It is not a density-competitive DRAM macro. It is a silicon-testable controller architecture for near-memory operations under an extreme area budget. The useful idea is the compromise: keep the ISA expressive enough for row moves, status/debug, low-precision vector operations, dot products, and MACs, but serialize the expensive arithmetic lanes enough that the design still routes locally.

## High-Level Design

- **Host interface:** a 32-bit SPI command frame enters through the TinyTapeout `ui_in`/`uo_out` pins. Responses are returned on the following SPI frame with status and read data.
- **Two independent channels:** each channel has its own control state, refresh timing, sticky error bit, pending command slot, bank pair, and accumulator.
- **Banked row store:** each channel contains two banks with two 8-bit rows per bank. `ACT`, `PRE`, `WR`, and `RD` expose a DRAM-like open-row programming model.
- **Near-bank processing unit:** the PU operates across the selected rows in the two banks. It supports bitwise vector ops, lane-wise add/subtract, lane sums, dot products, MAC, popcount, and XNOR-dot.
- **Variable compute resolution:** each compute command selects how an 8-bit row is interpreted: eight INT1 lanes, four signed INT2 lanes, two signed INT4 lanes, or one signed INT8 lane.
- **Host-driven row sequencing:** multi-row dot products are expressed as explicit `ACT` plus `DOT`/`MAC` commands for each row pair, preserving the operation while avoiding autonomous row-walk control state.

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

The demo uses explicit `DOT`/`MAC` row-pair sequencing to compute quantized dense-layer outputs and compares the result with a pure Python reference. Activation and weight precision can be configured independently; mixed-precision layers are executed at the wider lane precision, which preserves arithmetic while reducing packing density to the wider operand's lane count.

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

- Implements `VXOR`, `VAND`, `VOR`, `VADD`, `VSUB`, `DOT`, `MAC`, `SUM`, `POPCNT`, `XNORDOT`, and `ACC`
- Adds one pending command slot per channel for commands issued while `PIM busy` is high
- Preserves two channels and two banks per channel with two rows per bank for the `1x1` target branch
- Adds `CONFIG` subops to set/read each channel's automatic refresh reload counter and enable/disable automatic refresh
- Opcode `0x7` is reserved and sets sticky error
- Model/example tests: 24 passing
- Cocotb SPI RTL tests: 11 TinyTapeout-wrapper tests passing
- Synthesis: 4127 cells, total mapped area 56234.3796, lint-clean
- Official TinyTapeout area target: `1x1` tile for the reduced-depth feature set
- Local KLayout/Magic DRC: not yet rerun for this no-STREAM branch
- Routed standard-cell utilization: not yet measured for this no-STREAM branch
- Decision: removing autonomous row-walk control is the current 1x1 fitting experiment while preserving two channels and two banks per channel.

## Documentation

The canonical ISA reference is [docs/isa.md](docs/isa.md). Physical bring-up notes are in [docs/bringup.md](docs/bringup.md). Supporting architecture, timing, and physical checkpoint notes are in [docs/architecture.md](docs/architecture.md), [docs/timing.md](docs/timing.md), and [docs/area_log.md](docs/area_log.md).

## License

This project is released under the MIT License.
