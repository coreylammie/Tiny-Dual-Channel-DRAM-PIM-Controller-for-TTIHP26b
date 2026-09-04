"""Tiny DRAM-PIM controller ISA helpers shared by tests and host tooling."""

from dataclasses import dataclass
from enum import IntEnum


class Opcode(IntEnum):
    NOP = 0x0
    ACT = 0x1
    PRE = 0x2
    RD = 0x3
    WR = 0x4
    VOP = 0x5
    REDUCE = 0x6
    STREAM = 0x7
    ACC = 0x8
    REF = 0x9
    STATUS = 0xA
    CONFIG = 0xB
    ABORT = 0xC


class Precision(IntEnum):
    INT1 = 0
    INT2 = 1
    INT4 = 2
    INT8 = 3


class Vop(IntEnum):
    XOR = 0
    ADD = 1
    AND = 2
    OR = 3
    SUB = 4


class Reduce(IntEnum):
    DOT = 0
    MAC = 1
    SUM = 2
    POPCNT = 3
    XNORDOT = 4


@dataclass(frozen=True)
class Command:
    op: Opcode
    ch: int = 0
    subop: int = 0
    precision: Precision = Precision.INT1
    bank_a: int = 0
    bank_b: int = 0
    row_a: int = 0
    row_b: int = 0
    flags: int = 0
    imm8: int = 0

    def encode(self) -> int:
        return (
            ((int(self.op) & 0xF) << 28)
            | ((self.ch & 0x1) << 27)
            | ((self.subop & 0x7) << 24)
            | ((int(self.precision) & 0x3) << 22)
            | ((self.bank_a & 0x1) << 21)
            | ((self.bank_b & 0x1) << 20)
            | ((self.row_a & 0x3) << 18)
            | ((self.row_b & 0x3) << 16)
            | ((self.flags & 0x7) << 8)
            | (self.imm8 & 0xFF)
        )


def nop() -> Command:
    return Command(Opcode.NOP)


def act(ch: int, bank: int, row: int) -> Command:
    return Command(Opcode.ACT, ch=ch, bank_a=bank, row_a=row)


def pre(ch: int, bank: int) -> Command:
    return Command(Opcode.PRE, ch=ch, bank_a=bank)


def wr(ch: int, bank: int, value: int) -> Command:
    return Command(Opcode.WR, ch=ch, bank_a=bank, imm8=value)


def rd(ch: int, bank: int) -> Command:
    return Command(Opcode.RD, ch=ch, bank_a=bank)


def ref(ch: int, bank: int) -> Command:
    return Command(Opcode.REF, ch=ch, bank_a=bank)


def status(ch: int) -> Command:
    return Command(Opcode.STATUS, ch=ch)


def abort(ch: int) -> Command:
    return Command(Opcode.ABORT, ch=ch)


def config_refresh(ch: int, reload: int) -> Command:
    return Command(Opcode.CONFIG, ch=ch, subop=0, imm8=reload)


def config_read_refresh(ch: int) -> Command:
    return Command(Opcode.CONFIG, ch=ch, subop=1)


def config_auto_refresh(ch: int, enable: bool) -> Command:
    return Command(Opcode.CONFIG, ch=ch, subop=2, imm8=int(enable))


def config_read_auto_refresh(ch: int) -> Command:
    return Command(Opcode.CONFIG, ch=ch, subop=3)


def vop(
    ch: int,
    subop: Vop,
    precision: Precision,
    bank_a: int,
    bank_b: int,
    dest_bank: int = 0,
) -> Command:
    return Command(
        Opcode.VOP,
        ch=ch,
        subop=subop,
        precision=precision,
        bank_a=bank_a,
        bank_b=bank_b,
        flags=dest_bank & 1,
    )


def reduce_dot(ch: int, precision: Precision, bank_a: int, bank_b: int) -> Command:
    return Command(
        Opcode.REDUCE,
        ch=ch,
        subop=Reduce.DOT,
        precision=precision,
        bank_a=bank_a,
        bank_b=bank_b,
    )


def reduce_mac(ch: int, precision: Precision, bank_a: int, bank_b: int) -> Command:
    return Command(
        Opcode.REDUCE,
        ch=ch,
        subop=Reduce.MAC,
        precision=precision,
        bank_a=bank_a,
        bank_b=bank_b,
    )


def reduce_sum(ch: int, precision: Precision, bank: int) -> Command:
    return Command(
        Opcode.REDUCE,
        ch=ch,
        subop=Reduce.SUM,
        precision=precision,
        bank_a=bank,
    )


def reduce_popcnt(ch: int, bank: int) -> Command:
    return Command(
        Opcode.REDUCE,
        ch=ch,
        subop=Reduce.POPCNT,
        precision=Precision.INT1,
        bank_a=bank,
    )


def reduce_xnordot(ch: int, bank_a: int, bank_b: int) -> Command:
    return Command(
        Opcode.REDUCE,
        ch=ch,
        subop=Reduce.XNORDOT,
        precision=Precision.INT1,
        bank_a=bank_a,
        bank_b=bank_b,
    )


def stream(
    ch: int,
    subop: Reduce,
    precision: Precision,
    bank_a: int,
    bank_b: int,
    row_a: int,
    row_b: int,
    count: int,
) -> Command:
    return Command(
        Opcode.STREAM,
        ch=ch,
        subop=subop,
        precision=precision,
        bank_a=bank_a,
        bank_b=bank_b,
        row_a=row_a,
        row_b=row_b,
        imm8=count,
    )


def acc(ch: int, byte: int = 0) -> Command:
    return Command(Opcode.ACC, ch=ch, subop=byte & 0x3)
