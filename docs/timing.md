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
| Automatic refresh interval | Fixed 255 core clocks per channel; optionally disabled through `CONFIG` |

## Lane-Serial DOT/MAC Accumulator Checkpoint

The current RTL starts each PIM operation as an atomic channel operation. Refresh does not start while `PIM busy` is set.

| Operation | Precision | Busy cycles |
|---|---|---:|
| VADD | INT2/4 | 0 |
| ATTEND | INT2 | 4 |
| ATTEND | INT4 | 2 |
| DOT | INT1 | 1 |
| DOT | INT2 | 4 |
| DOT | INT4 | 2 |
| MAC | INT1 | 1 |
| MAC | INT2 | 4 |
| MAC | INT4 | 2 |
`VADD` updates the destination active row at command decode time. `ATTEND` reuses the shared lane stage and writes the packed lane result back to bank B after the final lane. `DOT` and `MAC` use the same lane-serial accumulator datapath. INT1 reduces all eight bit pairs through a popcount term in one busy cycle. INT2 and INT4 add one signed lane product per busy cycle. INT8 `VADD`, `ATTEND`, `DOT`, and `MAC` are reserved and set sticky error in the area-reduced `1x1` target. `DOT` clears the accumulator at operation start; `MAC` preserves the existing accumulator and adds into it.

Multi-row dot products and attention updates are host-driven sequences of `ACT`, `DOT`/`MAC`, and `ATTEND`; there is no autonomous row-walk command in the reduced `1x1` target branch.

## Refresh Control

`CONFIG subopcode 2` sets automatic refresh enable from `imm8[0]`; `CONFIG subopcode 3` reads the enable bit back. Disabling automatic refresh stops the autonomous counter from creating pending refresh work and clears pending/overdue refresh state. Forced `REF` commands still run. Reset enables automatic refresh with a fixed 255-core-clock interval. `ABORT` clears pending/busy/overdue refresh state but leaves the enable bit unchanged.
