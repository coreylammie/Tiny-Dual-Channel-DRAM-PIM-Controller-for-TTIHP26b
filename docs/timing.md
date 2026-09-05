# Timing

The Stage 2 baseline uses scaled architectural timing in the main TinyTapeout `clk` domain.

| Event | Latency |
|---|---:|
| SPI command frame | 32 SCLK rising edges sampled into `clk` |
| NOP | 1 core clock after decode |
| ACT | 1 core clock after decode |
| PRE | 1 core clock after decode |
| WR | 1 core clock after decode |
| RD | 1 core clock after decode, response available on next SPI frame |
| REF forced start | 1 core clock after decode |
| REF busy time | 4 core clocks |
| Automatic refresh interval | Configurable per channel and optionally disabled; reset default is enabled at 255 core clocks |

## Lane-Serial DOT/MAC Accumulator Checkpoint

The current RTL starts each PIM operation as an atomic channel operation. Refresh does not start while `PIM busy` is set.

| Operation | Precision | Busy cycles |
|---|---|---:|
| VXOR | INT1 | 8 |
| VXOR | INT2 | 4 |
| VXOR | INT4 | 2 |
| VXOR | INT8 | 1 |
| VADD | INT2 | 4 |
| VADD | INT4 | 2 |
| VADD | INT8 | 1 |
| VAND/VOR | INT1 | 8 |
| VAND/VOR | INT2 | 4 |
| VAND/VOR | INT4 | 2 |
| VAND/VOR | INT8 | 1 |
| VSUB | INT2 | 4 |
| VSUB | INT4 | 2 |
| VSUB | INT8 | 1 |
| SUM | INT1/2/4/8 | 1 |
| POPCNT | INT1 | 1 |
| XNORDOT | INT1 | 1 |
| DOT | INT1 | 1 |
| DOT | INT2 | 4 |
| DOT | INT4 | 2 |
| DOT | INT8 | 1 |
| MAC | INT1 | 1 |
| MAC | INT2 | 4 |
| MAC | INT4 | 2 |
| MAC | INT8 | 1 |
| STREAM.DOT | INT1 | 1 x row count |
| STREAM.DOT | INT2 | 4 x row count |
| STREAM.DOT | INT4 | 2 x row count |
| STREAM.DOT | INT8 | 1 x row count |
| STREAM.MAC | INT1 | 1 x row count |
| STREAM.MAC | INT2 | 4 x row count |
| STREAM.MAC | INT4 | 2 x row count |
| STREAM.MAC | INT8 | 1 x row count |

`DOT` and `MAC` use the same lane-serial accumulator datapath. INT1 reduces all eight bit pairs through a popcount term in one busy cycle. INT2, INT4, and INT8 add one signed lane product per busy cycle. `DOT` clears the accumulator at operation start; `MAC` preserves the existing accumulator and adds into it. This is the compromise between the rejected one-cycle full parallel dot-product path and the earlier 144-cycle one-bit serial carry path.

`STREAM.DOT` and `STREAM.MAC` reuse that same lane-serial engine across consecutive row pairs. `imm8[2:0]` selects a count from 1 through 2; count 0 is invalid. `STREAM.DOT` clears the accumulator once before the first row pair. `STREAM.MAC` keeps the previous accumulator value.

## Configurable Refresh

`CONFIG subopcode 0` writes the selected channel's refresh reload counter from `imm8`; `CONFIG subopcode 1` reads it back. The effective interval is `imm8 + 1` core clocks because a counter value of zero starts the refresh sequence and reloads from the configured value.

`CONFIG subopcode 2` sets automatic refresh enable from `imm8[0]`; `CONFIG subopcode 3` reads the enable bit back. Disabling automatic refresh stops the autonomous counter from creating pending refresh work and clears pending/overdue refresh state. Forced `REF` commands still run. Reset initializes the reload value to 254 and enables automatic refresh, so the default automatic refresh interval remains 255 core clocks. `ABORT` clears pending/busy/overdue refresh state but leaves the configured reload and enable values unchanged.
