from test.model import isa
from test.model.pim_model import TinyPimModel


def test_command_encoding_matches_documented_fields():
    cmd = isa.Command(
        isa.Opcode.WR,
        ch=1,
        subop=3,
        precision=isa.Precision.INT4,
        bank_a=1,
        bank_b=0,
        row_a=2,
        row_b=1,
        flags=5,
        imm8=0xA6,
    )
    assert cmd.encode() == 0x4B_A9_05A6


def test_bank_act_write_read_pre_sequence():
    model = TinyPimModel()
    assert model.execute(isa.act(0, 0, 1)) is None
    assert model.execute(isa.wr(0, 0, 0x5A)) is None
    assert model.execute(isa.rd(0, 0)) == 0x5A
    assert model.execute(isa.pre(0, 0)) is None
    assert model.execute(isa.rd(0, 0)) == 0
    assert model.channels[0].sticky_error


def test_two_row_geometry_preserves_independent_rows_and_rejects_row_two():
    model = TinyPimModel()
    assert model.execute(isa.act(0, 0, 0)) is None
    assert model.execute(isa.wr(0, 0, 0x2A)) is None
    assert model.execute(isa.act(0, 0, 1)) is None
    assert model.execute(isa.wr(0, 0, 0x3B)) is None
    assert model.execute(isa.act(0, 0, 0)) is None
    assert model.execute(isa.rd(0, 0)) == 0x2A
    assert model.execute(isa.act(0, 0, 1)) is None
    assert model.execute(isa.rd(0, 0)) == 0x3B
    assert not model.channels[0].sticky_error
    assert model.execute(isa.act(0, 0, 2)) is None
    assert model.channels[0].sticky_error


def test_channels_are_independent():
    model = TinyPimModel()
    model.execute(isa.act(0, 0, 1))
    model.execute(isa.wr(0, 0, 0x11))
    model.execute(isa.act(1, 0, 1))
    model.execute(isa.wr(1, 0, 0x22))
    assert model.execute(isa.rd(0, 0)) == 0x11
    assert model.execute(isa.rd(1, 0)) == 0x22


def test_refresh_blocks_target_bank_and_sets_error():
    model = TinyPimModel()
    model.execute(isa.act(0, 1, 0))
    model.execute(isa.ref(0, 1))
    model.execute(isa.wr(0, 1, 0x44))
    assert model.channels[0].sticky_error


def test_abort_clears_refresh_and_error_status():
    model = TinyPimModel()
    model.execute(isa.rd(0, 0))
    assert model.channels[0].sticky_error
    model.execute(isa.abort(0))
    assert model.channels[0].status() & 0xF0 == 0


def test_forced_refresh_sets_refresh_status():
    model = TinyPimModel()
    model.execute(isa.abort(0))
    model.execute(isa.ref(0, 1))
    assert model.channels[0].status() & 0x30


def test_config_is_reserved():
    model = TinyPimModel()
    model.execute(isa.abort(0))
    model.execute(isa.config_auto_refresh(0, False))
    assert model.channels[0].sticky_error


def open_and_write_pair(model, ch, a, b):
    model.execute(isa.abort(ch))
    model.execute(isa.act(ch, 0, 0))
    model.execute(isa.wr(ch, 0, a))
    model.execute(isa.act(ch, 1, 0))
    model.execute(isa.wr(ch, 1, b))


def test_vop_subopcode_zero_is_reserved():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0xA5, 0x3C)
    model.execute(isa.vop(1, isa.Vop.RESERVED_0, isa.Precision.INT1, 0, 1, dest_bank=0))
    assert model.channels[1].sticky_error
    assert model.execute(isa.rd(1, 0)) == 0xA5


def test_vop_subopcode_one_is_reserved():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0b01_10_11_00, 0b01_01_01_01)
    model.execute(isa.vop(1, isa.Vop.RESERVED_1, isa.Precision.INT2, 0, 1, dest_bank=0))
    assert model.channels[1].sticky_error
    assert model.execute(isa.rd(1, 0)) == 0b01_10_11_00


def test_attend_int4_uses_accumulator_score_to_update_state_row():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0x11, 0x11)
    model.execute(isa.reduce_dot(1, isa.Precision.INT4, 0, 1))

    model.execute(isa.wr(1, 0, 0x21))
    model.execute(isa.wr(1, 1, 0x10))
    model.execute(
        isa.vop(
            1,
            isa.Vop.ATTEND,
            isa.Precision.INT4,
            0,
            1,
        )
    )
    assert model.execute(isa.rd(1, 1)) == 0x52
    assert model.execute(isa.rd(1, 0)) == 0x21


def test_dot_int1_uses_unsigned_bit_semantics():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0b1010_1111, 0b1111_0001)
    model.execute(isa.reduce_dot(1, isa.Precision.INT1, 0, 1))
    assert model.execute(isa.acc(1, 0)) == 3
    assert model.execute(isa.acc(1, 1)) == 0


def test_mac_accumulates_dot_product():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0b1010_1111, 0b1111_0001)
    model.execute(isa.reduce_dot(1, isa.Precision.INT1, 0, 1))
    model.execute(isa.reduce_mac(1, isa.Precision.INT1, 0, 1))
    assert model.execute(isa.acc(1, 0)) == 6
    assert model.execute(isa.acc(1, 1)) == 0


def test_acc_subopcode_four_returns_byte_zero_and_clears_accumulator():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0b1010_1111, 0b1111_0001)
    model.execute(isa.reduce_dot(1, isa.Precision.INT1, 0, 1))

    assert model.execute(isa.acc(1, 4)) == 3
    assert model.execute(isa.acc(1, 0)) == 0


def test_dot_int4_uses_signed_lanes():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0x8F, 0x21)
    model.execute(isa.reduce_dot(1, isa.Precision.INT4, 0, 1))
    assert model.execute(isa.acc(1, 0)) == 0xEF
    assert model.execute(isa.acc(1, 1)) == 0x00
    assert model.execute(isa.acc(1, 2)) == 0x00


def test_dot_then_mac_sweeps_rows_under_host_control():
    model = TinyPimModel()
    model.execute(isa.abort(0))
    row_pairs = (
        (0b0000_0011, 0b0000_0101),
        (0b0000_1111, 0b0000_0011),
    )
    for row, (a, b) in enumerate(row_pairs):
        model.execute(isa.act(0, 0, row))
        model.execute(isa.wr(0, 0, a))
        model.execute(isa.act(0, 1, row))
        model.execute(isa.wr(0, 1, b))

    model.execute(isa.act(0, 0, 0))
    model.execute(isa.act(0, 1, 0))
    model.execute(isa.reduce_dot(0, isa.Precision.INT1, 0, 1))
    model.execute(isa.act(0, 0, 1))
    model.execute(isa.act(0, 1, 1))
    model.execute(isa.reduce_mac(0, isa.Precision.INT1, 0, 1))
    assert model.execute(isa.acc(0, 0)) == 3
    for row in range(2):
        model.execute(isa.act(0, 0, row))
        model.execute(isa.act(0, 1, row))
        model.execute(isa.reduce_mac(0, isa.Precision.INT1, 0, 1))
    assert model.execute(isa.acc(0, 0)) == 6


def test_reserved_opcode_sets_sticky_error():
    model = TinyPimModel()
    model.execute(isa.Command(isa.Opcode.RESERVED_7))
    assert model.channels[0].sticky_error


def test_attend_int1_is_invalid():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0x01, 0x01)
    model.execute(isa.vop(1, isa.Vop.ATTEND, isa.Precision.INT1, 0, 1, dest_bank=0))
    assert model.channels[1].sticky_error


def test_int2_compute_precision_is_reserved():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0x01, 0x55)
    model.execute(isa.vop(1, isa.Vop.ATTEND, isa.Precision.INT2, 0, 1, dest_bank=0))
    assert model.channels[1].sticky_error
    assert model.execute(isa.rd(1, 1)) == 0x55

    model.execute(isa.abort(1))
    open_and_write_pair(model, 1, 0x01, 0x01)
    model.execute(isa.reduce_dot(1, isa.Precision.INT2, 0, 1))
    assert model.channels[1].sticky_error

    model.execute(isa.abort(1))
    open_and_write_pair(model, 1, 0x01, 0x01)
    model.execute(isa.reduce_mac(1, isa.Precision.INT2, 0, 1))
    assert model.channels[1].sticky_error


def test_int8_compute_precision_is_reserved():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0x01, 0x01)
    model.execute(isa.vop(1, isa.Vop.ATTEND, isa.Precision.INT8, 0, 1, dest_bank=0))
    assert model.channels[1].sticky_error

    model.execute(isa.abort(1))
    open_and_write_pair(model, 1, 0x01, 0x01)
    model.execute(isa.reduce_dot(1, isa.Precision.INT8, 0, 1))
    assert model.channels[1].sticky_error

    model.execute(isa.abort(1))
    open_and_write_pair(model, 1, 0x01, 0x01)
    model.execute(isa.reduce_mac(1, isa.Precision.INT8, 0, 1))
    assert model.channels[1].sticky_error


def test_reserved_secondary_vop_subops_set_sticky_error():
    model = TinyPimModel()
    for subop in (
        isa.Vop.RESERVED_0,
        isa.Vop.RESERVED_1,
        isa.Vop.RESERVED_3,
        isa.Vop.RESERVED_4,
    ):
        model.execute(isa.abort(1))
        open_and_write_pair(model, 1, 0xA5, 0x3C)
        model.execute(isa.vop(1, subop, isa.Precision.INT4, 0, 1, dest_bank=0))
        assert model.channels[1].sticky_error


def test_reserved_secondary_reduce_subops_set_sticky_error():
    model = TinyPimModel()
    for subop in (isa.Reduce.RESERVED_2, isa.Reduce.RESERVED_3, isa.Reduce.RESERVED_4):
        model.execute(isa.abort(1))
        open_and_write_pair(model, 1, 0b1010_1111, 0b1111_0001)
        model.execute(
            isa.Command(
                isa.Opcode.REDUCE,
                ch=1,
                subop=subop,
                precision=isa.Precision.INT1,
                bank_a=0,
                bank_b=1,
            )
        )
        assert model.channels[1].sticky_error
