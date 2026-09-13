"""Architectural reference model for the DRAM-PIM controller."""

from dataclasses import dataclass, field
from typing import Optional

from .isa import Opcode, Command, Precision, Vop, Reduce

ROWS_PER_BANK = 2
BANKS_PER_CH = 2
REF_CYCLES = 4
ACC_WIDTH = 8


@dataclass
class Bank:
    rows: list[int] = field(default_factory=lambda: [0] * ROWS_PER_BANK)
    open: bool = False
    active_row: int = 0


@dataclass
class Channel:
    banks: list[Bank] = field(default_factory=lambda: [Bank(), Bank()])
    refresh_busy_ctr: int = 0
    refresh_bank: int = 0
    sticky_error: bool = False
    acc: int = 0

    def tick_refresh(self) -> None:
        if self.refresh_busy_ctr:
            self.refresh_busy_ctr -= 1

    def status(self) -> int:
        return (
            (int(self.sticky_error) << 7)
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

    def _attend(self, value: int, state: int, precision: Precision) -> int:
        if precision != Precision.INT4:
            self.sticky_error = True
            return 0
        bits = 4
        score_lane = self._sign_extend(self.acc & ((1 << bits) - 1), bits)
        lanes = [
            state_lane + value_lane * score_lane
            for value_lane, state_lane in zip(
                self._lane_values(value, precision),
                self._lane_values(state, precision),
            )
        ]
        return self._pack_lanes(lanes, bits)

    def _dot(self, a: int, b: int, precision: Precision) -> int:
        total = sum(
            av * bv
            for av, bv in zip(self._lane_values(a, precision), self._lane_values(b, precision))
        )
        return total & ((1 << ACC_WIDTH) - 1)

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
            if cmd.subop == Vop.ATTEND and cmd.precision == Precision.INT4:
                bank_b.rows[bank_b.active_row] = self._attend(
                    bank.rows[bank.active_row],
                    bank_b.rows[bank_b.active_row],
                    cmd.precision,
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
            if cmd.subop not in (Reduce.DOT, Reduce.MAC):
                self.sticky_error = True
            elif cmd.precision not in (Precision.INT1, Precision.INT4):
                self.sticky_error = True
            elif cmd.subop == Reduce.MAC:
                dot = self._dot(
                    bank.rows[bank.active_row],
                    bank_b.rows[bank_b.active_row],
                    cmd.precision,
                )
                self.acc = (self.acc + dot) & ((1 << ACC_WIDTH) - 1)
            else:
                self.acc = self._dot(
                    bank.rows[bank.active_row], bank_b.rows[bank_b.active_row], cmd.precision
                )
            return None
        if cmd.op == Opcode.ACC:
            result = self._acc_byte(cmd.subop & 0x3)
            if cmd.subop == 4:
                self.acc = 0
            return result
        if cmd.op == Opcode.REF:
            if self.refresh_busy_ctr:
                self.sticky_error = True
            else:
                self.refresh_busy_ctr = REF_CYCLES
                self.refresh_bank = cmd.bank_a
            return None
        if cmd.op == Opcode.STATUS:
            return self.status()
        if cmd.op == Opcode.CONFIG:
            self.sticky_error = True
            return None
        if cmd.op == Opcode.ABORT:
            self.refresh_busy_ctr = 0
            self.sticky_error = False
            self.acc = 0
            return None

        self.sticky_error = True
        return 0xFF


@dataclass
class TinyPimModel:
    channels: list[Channel] = field(default_factory=lambda: [Channel(), Channel()])

    def execute(self, cmd: Command) -> Optional[int]:
        return self.channels[cmd.ch].execute(cmd)
