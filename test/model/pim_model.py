"""Architectural reference model for the DRAM-PIM controller."""

from dataclasses import dataclass, field
from typing import Optional

from .isa import Opcode, Command, Precision, Vop, Reduce

ROWS_PER_BANK = 2
BANKS_PER_CH = 2
REF_INTERVAL = 255
REF_CYCLES = 4


@dataclass
class Bank:
    rows: list[int] = field(default_factory=lambda: [0] * ROWS_PER_BANK)
    open: bool = False
    active_row: int = 0


@dataclass
class Channel:
    phase: int
    banks: list[Bank] = field(default_factory=lambda: [Bank(), Bank()])
    refresh_ctr: int = 0
    refresh_reload: int = REF_INTERVAL - 1
    refresh_enable: bool = True
    refresh_busy_ctr: int = 0
    refresh_bank: int = 0
    refresh_pending: bool = False
    refresh_overdue: bool = False
    sticky_error: bool = False
    acc: int = 0

    def __post_init__(self) -> None:
        self.refresh_ctr = self.phase

    def tick_refresh(self) -> None:
        if self.refresh_enable:
            if self.refresh_ctr == 0:
                self.refresh_ctr = self.refresh_reload
                if self.refresh_busy_ctr or self.refresh_pending:
                    self.refresh_overdue = True
                else:
                    self.refresh_pending = True
            else:
                self.refresh_ctr -= 1

        if self.refresh_busy_ctr:
            self.refresh_busy_ctr -= 1
        elif self.refresh_pending:
            self.refresh_pending = False
            self.refresh_busy_ctr = REF_CYCLES
            self.refresh_bank ^= 1

    def status(self) -> int:
        return (
            (int(self.sticky_error) << 7)
            | (int(self.refresh_overdue) << 6)
            | (int(self.refresh_pending) << 5)
            | (int(bool(self.refresh_busy_ctr)) << 4)
            | (int(self.banks[1].open) << 2)
            | (int(self.banks[0].open) << 1)
        )

    def _lane_values(self, value: int, precision: Precision) -> list[int]:
        value &= 0xFF
        if precision == Precision.INT1:
            return [(value >> i) & 1 for i in range(8)]
        if precision == Precision.INT2:
            return [self._sign_extend((value >> (i * 2)) & 0x3, 2) for i in range(4)]
        if precision == Precision.INT4:
            return [self._sign_extend((value >> (i * 4)) & 0xF, 4) for i in range(2)]
        return [self._sign_extend(value, 8)]

    @staticmethod
    def _sign_extend(value: int, bits: int) -> int:
        sign = 1 << (bits - 1)
        return (value ^ sign) - sign

    @staticmethod
    def _pack_lanes(values: list[int], bits: int) -> int:
        mask = (1 << bits) - 1
        packed = 0
        for i, value in enumerate(values):
            packed |= (value & mask) << (i * bits)
        return packed & 0xFF

    def _vadd(self, a: int, b: int, precision: Precision) -> int:
        if precision == Precision.INT1:
            self.sticky_error = True
            return 0
        bits = {Precision.INT2: 2, Precision.INT4: 4, Precision.INT8: 8}[precision]
        lanes = [
            av + bv
            for av, bv in zip(self._lane_values(a, precision), self._lane_values(b, precision))
        ]
        return self._pack_lanes(lanes, bits)

    def _vsub(self, a: int, b: int, precision: Precision) -> int:
        if precision == Precision.INT1:
            self.sticky_error = True
            return 0
        bits = {Precision.INT2: 2, Precision.INT4: 4, Precision.INT8: 8}[precision]
        lanes = [
            av - bv
            for av, bv in zip(self._lane_values(a, precision), self._lane_values(b, precision))
        ]
        return self._pack_lanes(lanes, bits)

    def _dot(self, a: int, b: int, precision: Precision) -> int:
        total = sum(
            av * bv
            for av, bv in zip(self._lane_values(a, precision), self._lane_values(b, precision))
        )
        return total & ((1 << 18) - 1)

    def _sum(self, value: int, precision: Precision) -> int:
        return sum(self._lane_values(value, precision)) & ((1 << 18) - 1)

    def _popcnt(self, value: int) -> int:
        return bin(value & 0xFF).count("1")

    def _xnordot(self, a: int, b: int) -> int:
        return (2 * self._popcnt(~(a ^ b)) - 8) & ((1 << 18) - 1)

    def _acc_byte(self, byte: int) -> int:
        return (self.acc >> (8 * byte)) & 0xFF

    def execute(self, cmd: Command) -> Optional[int]:
        self.tick_refresh()
        bank = self.banks[cmd.bank_a]
        refreshing = bool(self.refresh_busy_ctr) and self.refresh_bank == cmd.bank_a

        if cmd.op == Opcode.NOP:
            return 0
        if cmd.op == Opcode.ACT:
            if refreshing or cmd.row_a >= ROWS_PER_BANK:
                self.sticky_error = True
            else:
                bank.open = True
                bank.active_row = cmd.row_a
            return None
        if cmd.op == Opcode.PRE:
            if refreshing:
                self.sticky_error = True
            else:
                bank.open = False
            return None
        if cmd.op == Opcode.WR:
            if not bank.open or refreshing:
                self.sticky_error = True
            else:
                bank.rows[bank.active_row] = cmd.imm8 & 0xFF
            return None
        if cmd.op == Opcode.RD:
            if not bank.open or refreshing:
                self.sticky_error = True
                return 0
            return bank.rows[bank.active_row]
        if cmd.op == Opcode.VOP:
            bank_b = self.banks[cmd.bank_b]
            refresh_b = bool(self.refresh_busy_ctr) and self.refresh_bank == cmd.bank_b
            if not bank.open or not bank_b.open or refreshing or refresh_b:
                self.sticky_error = True
                return None
            dest = self.banks[cmd.flags & 1]
            if cmd.subop == Vop.XOR:
                dest.rows[dest.active_row] = (
                    bank.rows[bank.active_row] ^ bank_b.rows[bank_b.active_row]
                ) & 0xFF
            elif cmd.subop == Vop.AND:
                dest.rows[dest.active_row] = (
                    bank.rows[bank.active_row] & bank_b.rows[bank_b.active_row]
                ) & 0xFF
            elif cmd.subop == Vop.OR:
                dest.rows[dest.active_row] = (
                    bank.rows[bank.active_row] | bank_b.rows[bank_b.active_row]
                ) & 0xFF
            elif cmd.subop == Vop.ADD and cmd.precision != Precision.INT1:
                dest.rows[dest.active_row] = self._vadd(
                    bank.rows[bank.active_row], bank_b.rows[bank_b.active_row], cmd.precision
                )
            elif cmd.subop == Vop.SUB and cmd.precision != Precision.INT1:
                dest.rows[dest.active_row] = self._vsub(
                    bank.rows[bank.active_row], bank_b.rows[bank_b.active_row], cmd.precision
                )
            else:
                self.sticky_error = True
            return None
        if cmd.op == Opcode.REDUCE:
            bank_b = self.banks[cmd.bank_b]
            refresh_b = bool(self.refresh_busy_ctr) and self.refresh_bank == cmd.bank_b
            if not bank.open or not bank_b.open or refreshing or refresh_b:
                self.sticky_error = True
                return None
            if cmd.subop not in (
                Reduce.DOT,
                Reduce.MAC,
                Reduce.SUM,
                Reduce.POPCNT,
                Reduce.XNORDOT,
            ):
                self.sticky_error = True
            elif cmd.subop == Reduce.SUM:
                self.acc = self._sum(bank.rows[bank.active_row], cmd.precision)
            elif cmd.subop == Reduce.POPCNT and cmd.precision == Precision.INT1:
                self.acc = self._popcnt(bank.rows[bank.active_row])
            elif cmd.subop == Reduce.XNORDOT and cmd.precision == Precision.INT1:
                self.acc = self._xnordot(bank.rows[bank.active_row], bank_b.rows[bank_b.active_row])
            elif cmd.subop in (Reduce.POPCNT, Reduce.XNORDOT):
                self.sticky_error = True
            elif cmd.subop == Reduce.MAC:
                dot = self._dot(
                    bank.rows[bank.active_row],
                    bank_b.rows[bank_b.active_row],
                    cmd.precision,
                )
                self.acc = (self.acc + dot) & ((1 << 18) - 1)
            else:
                self.acc = self._dot(
                    bank.rows[bank.active_row], bank_b.rows[bank_b.active_row], cmd.precision
                )
            return None
        if cmd.op == Opcode.STREAM:
            count = cmd.imm8 & 0x7
            if self.refresh_busy_ctr or self.refresh_pending:
                self.sticky_error = True
                return None
            if cmd.subop not in (Reduce.DOT, Reduce.MAC):
                self.sticky_error = True
                return None
            if count == 0 or cmd.row_a + count > ROWS_PER_BANK or cmd.row_b + count > ROWS_PER_BANK:
                self.sticky_error = True
                return None
            if cmd.subop == Reduce.DOT:
                self.acc = 0
            bank_b = self.banks[cmd.bank_b]
            for offset in range(count):
                row_a = cmd.row_a + offset
                row_b = cmd.row_b + offset
                bank.open = True
                bank.active_row = row_a
                bank_b.open = True
                bank_b.active_row = row_b
                self.acc = (
                    self.acc + self._dot(bank.rows[row_a], bank_b.rows[row_b], cmd.precision)
                ) & ((1 << 18) - 1)
            return None
        if cmd.op == Opcode.ACC:
            result = self._acc_byte(cmd.subop & 0x3)
            if cmd.subop == 4:
                self.acc = 0
            return result
        if cmd.op == Opcode.REF:
            if self.refresh_busy_ctr:
                self.refresh_overdue = True
            else:
                self.refresh_busy_ctr = REF_CYCLES
                self.refresh_bank = cmd.bank_a
                self.refresh_pending = False
            return None
        if cmd.op == Opcode.STATUS:
            return self.status()
        if cmd.op == Opcode.CONFIG:
            if cmd.subop == 0:
                self.refresh_reload = cmd.imm8 & 0xFF
                self.refresh_ctr = self.refresh_reload
            elif cmd.subop == 1:
                return self.refresh_reload
            elif cmd.subop == 2:
                self.refresh_enable = bool(cmd.imm8 & 1)
                self.refresh_ctr = self.refresh_reload
                if not self.refresh_enable:
                    self.refresh_pending = False
                    self.refresh_overdue = False
            elif cmd.subop == 3:
                return int(self.refresh_enable)
            else:
                self.sticky_error = True
            return None
        if cmd.op == Opcode.ABORT:
            self.refresh_pending = False
            self.refresh_busy_ctr = 0
            self.refresh_overdue = False
            self.sticky_error = False
            self.acc = 0
            return None

        self.sticky_error = True
        return 0xFF


@dataclass
class TinyPimModel:
    channels: list[Channel] = field(default_factory=lambda: [Channel(0), Channel(32)])

    def execute(self, cmd: Command) -> Optional[int]:
        return self.channels[cmd.ch].execute(cmd)
