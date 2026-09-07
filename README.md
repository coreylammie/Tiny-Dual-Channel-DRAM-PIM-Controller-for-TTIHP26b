# Tiny Dual-Channel DRAM-PIM Controller for TTIHP26b

This project asks a deliberately small question: how much of a DRAM processing-in-memory controller can fit in a tiny TinyTapeout IHP standard-cell macro?

The result is a tiny dual-channel DRAM-PIM controller with real memory-control behavior, refresh state, and cross-bank compute. It is not a density-competitive DRAM macro. It is a silicon-testable controller architecture for near-memory operations under an extreme area budget. The useful idea is the compromise: keep the ISA expressive enough for row moves, status/debug, low-precision vector operations, dot products, and MACs, but serialize the expensive arithmetic lanes enough that the design still routes locally.

## High-Level Design

- **Host interface:** a 32-bit SPI command frame enters through the TinyTapeout `ui_in`/`uo_out` pins. Responses are returned on the following SPI frame with status and read data.
- **Two independent channels:** each channel has its own control state, fixed-period refresh state, sticky error bit, bank pair, and 14-bit accumulator.
- **Banked row store:** each channel contains two banks with two 8-bit rows per bank. `ACT`, `PRE`, `WR`, and `RD` expose a DRAM-like open-row programming model.
- **Shared near-bank processing unit:** one lane-serial PU is multiplexed between the two channels. `VXOR` and lane-wise `VADD` are immediate row-transform commands; `DOT` and `MAC` use the shared multi-cycle accumulator stage.
- **Variable compute resolution:** each compute command selects how an 8-bit row is interpreted: eight INT1 lanes, four signed INT2 lanes, or two signed INT4 lanes. INT8 remains encoded but is reserved for compute in the `1x1` target branch.
- **Host-driven row sequencing:** multi-row dot products are expressed as explicit `ACT` plus `DOT`/`MAC` commands for each row pair, preserving the operation while avoiding autonomous row-walk control state.

The implementation keeps the visible ISA relatively expressive, but uses one shared lane-serial DOT/MAC datapath so the design remains small enough to target the TinyTapeout IHP area budget.

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

- Implements `VXOR`, `VADD`, `DOT`, `MAC`, and `ACC`
- Commands issued while the shared PIM operation is busy set sticky error and are dropped
- Preserves two channels and two banks per channel with two rows per bank for the `1x1` target branch
- Adds `CONFIG` subops to enable/disable automatic refresh and read back that enable bit
- Uses only `uo_out[0]` for SPI MISO; remaining output pins are tied low and status is read over SPI
- Opcode `0x7` is reserved and sets sticky error
- Model/example tests: 24 passing
- Cocotb SPI RTL tests: 10 TinyTapeout-wrapper tests passing
- Synthesis: 1679 cells, total mapped area 28317.1518, lint-clean
- Official TinyTapeout area target: `1x1` tile for the reduced-depth feature set
- Latest official TinyTapeout `1x1` GDS check: failed global placement at 106.525% utilization after tying off spare outputs and mirroring placement knobs
- Local KLayout/Magic DRC: not yet rerun for this no-STREAM branch
- Routed standard-cell utilization: not yet measured for this no-STREAM branch
- Decision: the current 1x1 fitting experiment preserves two channels and two banks per channel, keeps INT1/INT2/INT4 DOT/MAC, reserves INT8 compute, narrows each channel accumulator to 14 bits, and shares one PU between both channels to reduce area.

## Documentation

The canonical ISA reference is [docs/isa.md](docs/isa.md). Physical bring-up notes are in [docs/bringup.md](docs/bringup.md). Supporting architecture, timing, and physical checkpoint notes are in [docs/architecture.md](docs/architecture.md), [docs/timing.md](docs/timing.md), and [docs/area_log.md](docs/area_log.md).

## License

This project is released under the MIT License.
