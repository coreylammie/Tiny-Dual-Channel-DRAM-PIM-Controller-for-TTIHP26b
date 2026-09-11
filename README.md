# Tiny Dual-Channel DRAM-PIM Controller for TTIHP26b

This project asks a deliberately small question: how much of a DRAM processing-in-memory controller can fit in a tiny TinyTapeout IHP standard-cell macro?

The result is a tiny dual-channel DRAM-PIM controller with real memory-control behavior, explicit refresh, and cross-bank compute. It is not a density-competitive DRAM macro. It is a silicon-testable controller architecture for near-memory operations under an extreme area budget. The useful idea is the compromise: keep the ISA expressive enough for row moves, status/debug, dot products, MACs, and experimental attention updates, but serialize or reuse the expensive arithmetic lanes enough that the design can still be evaluated against a TinyTapeout tile.

## High-Level Design

- **Host interface:** a 32-bit SPI command frame enters through the TinyTapeout `ui_in`/`uo_out` pins. Responses are returned on the following SPI frame with status and read data.
- **Two independent channels:** each channel has its own control state, forced-refresh state, sticky error bit, bank pair, and 8-bit accumulator.
- **Banked row store:** each channel contains two banks with two 8-bit rows per bank. `ACT`, `PRE`, `WR`, and `RD` expose a DRAM-like open-row programming model.
- **Shared near-bank processing unit:** one PU is multiplexed between the two channels. Experimental `ATTEND`, `DOT`, and `MAC` use the shared multi-cycle lane stage.
- **Variable compute resolution:** each compute command selects how an 8-bit row is interpreted: eight INT1 lanes or two signed INT4 lanes. INT2 and INT8 remain encoded but are reserved for compute in the `1x1` target branch.
- **Host-driven row sequencing:** multi-row dot products and attention updates are expressed as explicit row activations plus PU commands, preserving the compute primitive while avoiding autonomous row-walk control state.

The experimental `ATTEND` operation is intended as a tiny analogue of attention-value accumulation: after `DOT` or `MAC` computes an attention score in `ACC`, `ATTEND` updates `bank_b_active_row = bank_b_active_row + bank_a_active_row * ACC_low`, evaluated through the shared lane stage at INT4 precision.

## Quick Start

Run fast model and example tests:

```sh
python -m pytest test/test_model.py test/test_dense_layer_demo.py
```

Run a dense-layer inference demo against the controller model:

```sh
python examples/dense_layer_demo.py
```

The demo uses explicit `DOT`/`MAC` row-pair sequencing to compute quantized dense-layer outputs and compares the result with a pure Python reference. Activation and weight precision can be configured independently; mixed-precision layers are promoted to the nearest supported execution precision, which preserves arithmetic while reducing packing density to the execution lane count.

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

- Implements experimental `ATTEND`, `DOT`, `MAC`, and `ACC`; `VOP` subopcode 1 is reserved on this area-focused branch
- Commands issued while the shared PIM operation is busy set sticky error and are dropped
- Preserves two channels and two banks per channel with two rows per bank for the `1x1` target branch
- Uses explicit host-issued `REF`; `CONFIG` is reserved on this area-focused branch
- Uses only `uo_out[0]` for SPI MISO; remaining output pins are tied low and status is read over SPI
- Opcode `0x7` is reserved and sets sticky error
- Model/example tests: 26 passing
- Cocotb SPI RTL tests: 11 TinyTapeout-wrapper tests passing
- Synthesis: 1514 cells, total mapped area 25579.1844, lint-clean on this experimental branch
- Official TinyTapeout area target: `1x1` tile for the reduced-depth feature set
- Latest official TinyTapeout `1x1` GDS check: passing, including precheck, gate-level test, and viewer generation
- Magic DRC/LVS/antenna: 0 errors after official GDS build; KLayout DRC is disabled in the current TinyTapeout IHP flow
- Routed standard-cell utilization: 95.304% in the official TinyTapeout GDS build
- Decision: this attention-focused experiment preserves two channels and two banks per channel, keeps INT1/INT4 DOT/MAC plus accumulator-fed INT4 `ATTEND`, reserves INT2/INT8 compute and the generic `VADD` slot, narrows each channel accumulator to 8 bits, and shares one PU between both channels to reduce area.

## Documentation

The canonical ISA reference is [docs/isa.md](docs/isa.md). Physical bring-up notes are in [docs/bringup.md](docs/bringup.md). Supporting architecture, timing, and physical checkpoint notes are in [docs/architecture.md](docs/architecture.md), [docs/timing.md](docs/timing.md), and [docs/area_log.md](docs/area_log.md).

## License

This project is released under the MIT License.
