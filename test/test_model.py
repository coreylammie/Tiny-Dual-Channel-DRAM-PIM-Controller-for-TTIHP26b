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
    model.execute(isa.wr(0, 1, 0x44))
    assert model.channels[0].sticky_error


def test_abort_clears_refresh_and_error_status():
    model = TinyPimModel()
    model.execute(isa.rd(0, 0))
    assert model.channels[0].sticky_error
    model.execute(isa.abort(0))
    assert model.channels[0].status() & 0xF0 == 0


def test_config_refresh_reload_can_force_overdue_status():
    model = TinyPimModel()
    model.execute(isa.abort(0))
    model.execute(isa.config_refresh(0, 1))
    for _ in range(5):
        model.execute(isa.nop())
    assert model.channels[0].status() & 0x40


def test_config_reads_reload_and_can_disable_auto_refresh():
    model = TinyPimModel()
    model.execute(isa.abort(0))
    model.execute(isa.config_refresh(0, 2))
    assert model.execute(isa.config_read_refresh(0)) == 2
    assert model.execute(isa.config_read_auto_refresh(0)) == 1
    model.execute(isa.config_auto_refresh(0, False))
    assert model.execute(isa.config_read_auto_refresh(0)) == 0
    for _ in range(12):
        model.execute(isa.nop())
    assert model.channels[0].status() & 0x70 == 0
    model.execute(isa.config_auto_refresh(0, True))
    assert model.execute(isa.config_read_auto_refresh(0)) == 1


def open_and_write_pair(model, ch, a, b):
    model.execute(isa.abort(ch))
    model.execute(isa.act(ch, 0, 0))
    model.execute(isa.wr(ch, 0, a))
    model.execute(isa.act(ch, 1, 0))
    model.execute(isa.wr(ch, 1, b))


def test_vxor_writes_selected_destination_bank():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0xA5, 0x3C)
    model.execute(isa.vop(1, isa.Vop.XOR, isa.Precision.INT1, 0, 1, dest_bank=0))
    assert model.execute(isa.rd(1, 0)) == 0x99


def test_vadd_int2_wraps_each_lane():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0b01_10_11_00, 0b01_01_01_01)
    model.execute(isa.vop(1, isa.Vop.ADD, isa.Precision.INT2, 0, 1, dest_bank=0))
    assert model.execute(isa.rd(1, 0)) == 0b10_11_00_01


def test_vadd_int4_wraps_each_lane():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0x7F, 0x11)
    model.execute(isa.vop(1, isa.Vop.ADD, isa.Precision.INT4, 0, 1, dest_bank=1))
    assert model.execute(isa.rd(1, 1)) == 0x80


def test_boolean_vops_write_selected_destination_bank():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0xA5, 0x3C)
    model.execute(isa.vop(1, isa.Vop.AND, isa.Precision.INT1, 0, 1, dest_bank=0))
    assert model.execute(isa.rd(1, 0)) == 0x24
    model.execute(isa.vop(1, isa.Vop.OR, isa.Precision.INT1, 0, 1, dest_bank=1))
    assert model.execute(isa.rd(1, 1)) == 0x3C


def test_vsub_int4_wraps_each_lane():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0x10, 0x21)
    model.execute(isa.vop(1, isa.Vop.SUB, isa.Precision.INT4, 0, 1, dest_bank=0))
    assert model.execute(isa.rd(1, 0)) == 0xFF


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


def test_dot_int4_uses_signed_lanes():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0x8F, 0x21)
    model.execute(isa.reduce_dot(1, isa.Precision.INT4, 0, 1))
    assert model.execute(isa.acc(1, 0)) == 0xEF
    assert model.execute(isa.acc(1, 1)) == 0xFF
    assert model.execute(isa.acc(1, 2)) == 0x03


def test_sum_popcnt_and_xnordot_reductions():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0b1010_1111, 0b1111_0001)
    model.execute(isa.reduce_sum(1, isa.Precision.INT1, 0))
    assert model.execute(isa.acc(1, 0)) == 6
    model.execute(isa.reduce_popcnt(1, 1))
    assert model.execute(isa.acc(1, 0)) == 5
    model.execute(isa.reduce_xnordot(1, 0, 1))
    assert model.execute(isa.acc(1, 0)) == 0xFE
    assert model.execute(isa.acc(1, 1)) == 0xFF


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


def test_vadd_int1_is_invalid():
    model = TinyPimModel()
    open_and_write_pair(model, 1, 0x01, 0x01)
    model.execute(isa.vop(1, isa.Vop.ADD, isa.Precision.INT1, 0, 1, dest_bank=0))
    assert model.channels[1].sticky_error
