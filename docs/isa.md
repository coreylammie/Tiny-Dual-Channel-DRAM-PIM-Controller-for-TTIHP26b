# ISA

Commands are fixed 32-bit SPI words, MSB first. Responses are shifted out on the next SPI frame.

## Encoding

| Bits | Field |
|---|---|
| 31:28 | major opcode |
| 27 | channel |
| 26:24 | subopcode |
| 23:22 | precision |
| 21 | bank A |
| 20 | bank B / destination |
| 19:18 | row A |
| 17:16 | reserved row B field |
| 15:11 | reserved |
| 10:8 | flags |
| 7:0 | immediate data |

The reduced `1x1` target geometry implements row values 0 through 1 for `row A`. Row values 2 and 3 are encoded but currently invalid. The current RTL operates on the active row of `bank B`, so bits 17:16 are reserved for future row-walk or direct row-pair operations.

## Opcodes

| Opcode | Mnemonic | Behavior |
|---:|---|---|
| 0x0 | NOP | Responds with zero |
| 0x1 | ACT | Opens `bank A` at `row A` |
| 0x2 | PRE | Closes `bank A` |
| 0x3 | RD | Reads active row from `bank A` |
| 0x4 | WR | Writes `imm8` to active row in `bank A` |
| 0x5 | VOP | Vector PIM operation selected by `subopcode` |
| 0x6 | REDUCE | Reduction PIM operation selected by `subopcode` |
| 0x7 | RESERVED | Reserved; sets sticky error |
| 0x8 | ACC | Reads accumulator byte selected by `subopcode[1:0]` |
| 0x9 | REF | Forces refresh on `bank A` |
| 0xA | STATUS | Reads channel status |
| 0xB | CONFIG | Configuration operation selected by `subopcode` |
| 0xC | ABORT | Clears sticky error and refresh state |

## Precision

`00` is INT1, `01` is INT2, `10` is INT4, and `11` is INT8.

## PU Suboperations

`VOP` uses the two active rows selected by `bank A` and `bank B`. Both banks must be open and not refreshing. `flags[0]` selects the destination bank for writeback.

| Opcode | Subopcode | Mnemonic | Precision | Side effect |
|---|---:|---|---|---|
| VOP | 0 | VXOR | INT1/2/4/8 | bitwise XOR writes destination active row |
| VOP | 1 | VADD | INT2/4/8 | lane-wise wraparound add writes destination active row |
| VOP | 2 | VAND | INT1/2/4/8 | bitwise AND writes destination active row |
| VOP | 3 | VOR | INT1/2/4/8 | bitwise OR writes destination active row |
| VOP | 4 | VSUB | INT2/4/8 | lane-wise wraparound subtract writes destination active row |
| REDUCE | 0 | DOT | INT1/2/4/8 | writes 18-bit accumulator |
| REDUCE | 1 | MAC | INT1/2/4/8 | accumulates dot product into 18-bit accumulator |
| REDUCE | 2 | SUM | INT1/2/4/8 | sums active `bank A` row lanes into 18-bit accumulator |
| REDUCE | 3 | POPCNT | INT1 | popcounts active `bank A` row into 18-bit accumulator |
| REDUCE | 4 | XNORDOT | INT1 | writes `2 * popcount(XNOR(A,B)) - 8` into 18-bit accumulator |

`DOT.INT1` and `MAC.INT1` treat row bits as unsigned `{0,1}` lanes. `DOT.INT2/4/8` and `MAC.INT2/4/8` use signed two's-complement lanes. The RTL computes INT1 as a one-cycle bit-popcount term and computes INT2/4/8 through one signed lane product per busy cycle. `DOT` clears the accumulator before adding the dot product; `MAC` preserves the existing accumulator and adds into it.

All `REDUCE` operations require both selected banks to be open and not refreshing. `SUM` and `POPCNT` consume only the active `bank A` row, but still use that shared REDUCE readiness check. Multi-row dot products are host-driven by activating each row pair and issuing `DOT` for the first row pair followed by `MAC` for subsequent row pairs.

`ACC` returns accumulator byte 0, 1, or 2 using `subopcode[1:0]`. `subopcode == 4` clears the accumulator after returning byte 0.

## Configuration

| CONFIG Subopcode | Mnemonic | Response | Behavior |
|---:|---|---|---|
| 0 | REF_RELOAD_WR | none | sets automatic refresh reload counter to `imm8` |
| 1 | REF_RELOAD_RD | reload value | returns automatic refresh reload counter |
| 2 | REF_AUTO_WR | none | sets automatic refresh enable from `imm8[0]` |
| 3 | REF_AUTO_RD | bit 0 | returns automatic refresh enable |

The effective refresh interval is `reload + 1` core clocks because the counter reloads after reaching zero. Reset uses reload value 254 and automatic refresh enabled, giving the default 255-core-clock automatic refresh interval. `REF_AUTO_WR` disables only automatic refresh scheduling; forced `REF` commands still work. Unsupported `CONFIG` subopcodes set sticky error.

## Response Word

Responses are returned on the next SPI transaction:

```text
[31:24] tag: 0xA0 for channel 0, 0xA1 for channel 1
[23:16] channel status
[15:8]  reserved
[7:0]   response data
```

For ordinary command acknowledgements without read data, the top level returns:

```text
[31:24] 0x55
[23:16] channel 1 status
[15:8]  channel 0 status
[7:0]   0x00
```

## Status Byte

| Bit | Meaning |
|---|---|
| 7 | sticky error |
| 6 | refresh overdue |
| 5 | refresh pending |
| 4 | refresh busy |
| 3 | PIM busy |
| 2 | bank 1 open |
| 1 | bank 0 open |
| 0 | pending command queued |
