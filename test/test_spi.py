import os

import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import RisingEdge

from test.model import isa
from test.model.spi_driver import SpiDriver

GATE_LEVEL = os.environ.get("GATES") == "yes"


def user_design(dut):
    try:
        return dut.user_project
    except AttributeError:
        return dut


async def reset(dut):
    dut.ena.value = 1
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    dut.ui_in.value = 0x02
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def wait_core_clocks(dut, cycles):
    for _ in range(cycles):
        await RisingEdge(dut.clk)


def pack_lanes(values, precision):
    if precision == isa.Precision.INT1:
        packed = 0
        for idx, value in enumerate(values):
            assert value in (0, 1)
            packed |= value << idx
        return packed & 0xFF

    bits = {
        isa.Precision.INT2: 2,
        isa.Precision.INT4: 4,
        isa.Precision.INT8: 8,
    }[precision]
    packed = 0
    for idx, value in enumerate(values):
        assert -(1 << (bits - 1)) <= value <= (1 << (bits - 1)) - 1
        packed |= (value & ((1 << bits) - 1)) << (idx * bits)
    return packed & 0xFF


def sign_extend(value, bits):
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


async def write_packed_rows(spi, ch, bank, rows):
    for row, value in enumerate(rows):
        await spi.transfer32(isa.act(ch, bank, row).encode())
        await spi.transfer32(isa.wr(ch, bank, value).encode())


async def read_acc18(spi, ch):
    await spi.transfer32(isa.acc(ch, 0).encode())
    acc0_rsp = await spi.transfer32(isa.acc(ch, 1).encode())
    acc1_rsp = await spi.transfer32(isa.acc(ch, 2).encode())
    acc2_rsp = await spi.transfer32(isa.nop().encode())
    raw = (acc0_rsp & 0xFF) | ((acc1_rsp & 0xFF) << 8) | ((acc2_rsp & 0x03) << 16)
    return sign_extend(raw, 18)


async def status_response(spi, ch):
    await spi.transfer32(isa.status(ch).encode())
    return await spi.transfer32(isa.nop().encode())


@cocotb.test()
async def spi_back_to_back_status_frames(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    spi = SpiDriver(dut)

    first = await spi.transfer32(isa.status(0).encode())
    second = await spi.transfer32(isa.status(0).encode())

    assert first == 0
    assert (second >> 24) == 0xA0


@cocotb.test()
async def spi_act_write_read_row_one(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    spi = SpiDriver(dut)

    await spi.transfer32(isa.act(0, 0, 1).encode())
    await spi.transfer32(isa.wr(0, 0, 0x5A).encode())
    await spi.transfer32(isa.rd(0, 0).encode())
    rsp = await spi.transfer32(isa.nop().encode())

    assert (rsp >> 24) == 0xA0
    assert (rsp & 0xFF) == 0x5A


@cocotb.test()
async def spi_routes_to_channel_one(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    spi = SpiDriver(dut)

    await spi.transfer32(isa.act(1, 1, 1).encode())
    await spi.transfer32(isa.wr(1, 1, 0xC3).encode())
    await spi.transfer32(isa.rd(1, 1).encode())
    rsp = await spi.transfer32(isa.nop().encode())

    assert (rsp >> 24) == 0xA1
    assert (rsp & 0xFF) == 0xC3


@cocotb.test(skip=GATE_LEVEL)
async def spi_queues_one_command_while_pim_busy(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    spi = SpiDriver(dut)

    await spi.transfer32(isa.abort(0).encode())
    await spi.transfer32(isa.act(0, 0, 1).encode())
    await spi.transfer32(isa.wr(0, 0, 0b1010_1111).encode())
    await spi.transfer32(isa.act(0, 1, 1).encode())
    await spi.transfer32(isa.wr(0, 1, 0b1111_0001).encode())
    await spi.transfer32(isa.reduce_dot(0, isa.Precision.INT1, 0, 1).encode())

    await RisingEdge(dut.clk)
    design = user_design(dut)
    design.cmd_word.value = Force(isa.status(0).encode())
    design.cmd_valid.value = Force(1)
    await RisingEdge(dut.clk)
    design.cmd_valid.value = Release()
    design.cmd_word.value = Release()

    await wait_core_clocks(dut, 160)

    rsp = await spi.transfer32(isa.nop().encode())

    assert (rsp >> 24) == 0xA0
    assert ((rsp >> 16) & 0x80) == 0
    assert (rsp & 0x80) == 0


@cocotb.test()
async def spi_reduce_mac_accumulates_dot(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    spi = SpiDriver(dut)

    await spi.transfer32(isa.abort(0).encode())
    await spi.transfer32(isa.act(0, 0, 1).encode())
    await spi.transfer32(isa.wr(0, 0, 0b1010_1111).encode())
    await spi.transfer32(isa.act(0, 1, 1).encode())
    await spi.transfer32(isa.wr(0, 1, 0b1111_0001).encode())

    await spi.transfer32(isa.reduce_dot(0, isa.Precision.INT1, 0, 1).encode())
    await wait_core_clocks(dut, 160)
    await spi.transfer32(isa.acc(0, 0).encode())
    dot_rsp = await spi.transfer32(isa.nop().encode())

    await spi.transfer32(isa.reduce_mac(0, isa.Precision.INT1, 0, 1).encode())
    await wait_core_clocks(dut, 160)
    await spi.transfer32(isa.acc(0, 0).encode())
    mac_rsp = await spi.transfer32(isa.nop().encode())

    assert (dot_rsp >> 24) == 0xA0
    assert (dot_rsp & 0xFF) == 3
    assert (mac_rsp >> 24) == 0xA0
    assert (mac_rsp & 0xFF) == 6


@cocotb.test()
async def spi_config_refresh_reload_sets_overdue(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    spi = SpiDriver(dut)

    await spi.transfer32(isa.abort(0).encode())
    await spi.transfer32(isa.config_refresh(0, 2).encode())
    await spi.transfer32(isa.config_read_refresh(0).encode())
    reload_rsp = await spi.transfer32(isa.nop().encode())

    await spi.transfer32(isa.config_auto_refresh(0, False).encode())
    await wait_core_clocks(dut, 12)
    await spi.transfer32(isa.status(0).encode())
    disabled_rsp = await spi.transfer32(isa.nop().encode())

    await spi.transfer32(isa.config_auto_refresh(0, True).encode())
    await spi.transfer32(isa.config_read_auto_refresh(0).encode())
    enable_rsp = await spi.transfer32(isa.nop().encode())

    await spi.transfer32(isa.config_refresh(0, 1).encode())
    await wait_core_clocks(dut, 12)
    await spi.transfer32(isa.status(0).encode())
    rsp = await spi.transfer32(isa.nop().encode())

    assert (reload_rsp >> 24) == 0xA0
    assert (reload_rsp & 0xFF) == 2
    assert ((disabled_rsp >> 16) & 0x40) == 0
    assert (enable_rsp & 0xFF) == 1
    assert (rsp >> 24) == 0xA0
    assert ((rsp >> 16) & 0x40) != 0


@cocotb.test()
async def spi_extra_pim_ops_and_stream_dot(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    spi = SpiDriver(dut)

    await spi.transfer32(isa.abort(0).encode())
    await spi.transfer32(isa.act(0, 0, 0).encode())
    await spi.transfer32(isa.wr(0, 0, 0b0000_0011).encode())
    await spi.transfer32(isa.act(0, 1, 0).encode())
    await spi.transfer32(isa.wr(0, 1, 0b0000_0101).encode())
    await spi.transfer32(isa.act(0, 0, 1).encode())
    await spi.transfer32(isa.wr(0, 0, 0b0000_1111).encode())
    await spi.transfer32(isa.act(0, 1, 1).encode())
    await spi.transfer32(isa.wr(0, 1, 0b0000_0011).encode())
    await spi.transfer32(isa.stream(0, isa.Reduce.DOT, isa.Precision.INT1, 0, 1, 0, 0, 2).encode())
    await wait_core_clocks(dut, 620)
    await spi.transfer32(isa.acc(0, 0).encode())
    stream_rsp = await spi.transfer32(isa.nop().encode())

    await spi.transfer32(isa.reduce_popcnt(0, 0).encode())
    await spi.transfer32(isa.acc(0, 0).encode())
    popcnt_rsp = await spi.transfer32(isa.nop().encode())

    await spi.transfer32(isa.reduce_xnordot(0, 0, 1).encode())
    await spi.transfer32(isa.acc(0, 0).encode())
    xnor_rsp = await spi.transfer32(isa.nop().encode())

    await spi.transfer32(isa.vop(0, isa.Vop.SUB, isa.Precision.INT4, 0, 1, dest_bank=0).encode())
    await wait_core_clocks(dut, 8)
    await spi.transfer32(isa.rd(0, 0).encode())
    sub_rsp = await spi.transfer32(isa.nop().encode())

    assert (stream_rsp >> 24) == 0xA0
    assert (stream_rsp & 0xFF) == 3
    assert (popcnt_rsp & 0xFF) == 4
    assert (xnor_rsp & 0xFF) == 0x04
    assert (sub_rsp & 0xFF) == 0x0C


@cocotb.test()
async def spi_dense_layer_mixed_precision_stream_dot(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    spi = SpiDriver(dut)

    ch = 0
    activation_precision = isa.Precision.INT4
    weight_precision = isa.Precision.INT2
    execution_precision = isa.Precision.INT4
    lanes_per_row = 2
    activations = [1, -2, 3, 0]
    weights = [
        [1, -1, 1, 0],
        [-1, 0, 1, -2],
    ]
    bias = [1, -2]
    expected_dot = [
        sum(a * w for a, w in zip(activations, output_weights)) for output_weights in weights
    ]
    expected_dense = [dot + b for dot, b in zip(expected_dot, bias)]

    assert activation_precision == execution_precision
    assert weight_precision < execution_precision

    activation_rows = [
        pack_lanes(activations[row : row + lanes_per_row], execution_precision)
        for row in range(0, len(activations), lanes_per_row)
    ]

    actual_dot = []
    for output_weights in weights:
        await spi.transfer32(isa.abort(ch).encode())
        await spi.transfer32(isa.config_auto_refresh(ch, False).encode())
        await write_packed_rows(spi, ch, 0, activation_rows)

        weight_rows = [
            pack_lanes(output_weights[row : row + lanes_per_row], execution_precision)
            for row in range(0, len(output_weights), lanes_per_row)
        ]
        await write_packed_rows(spi, ch, 1, weight_rows)

        await spi.transfer32(
            isa.stream(
                ch,
                isa.Reduce.DOT,
                execution_precision,
                0,
                1,
                0,
                0,
                len(activation_rows),
            ).encode()
        )
        await wait_core_clocks(dut, 80)
        actual_dot.append(await read_acc18(spi, ch))

    actual_dense = [dot + b for dot, b in zip(actual_dot, bias)]

    assert actual_dot == expected_dot
    assert actual_dense == expected_dense


@cocotb.test()
async def spi_unopened_read_sets_sticky_error_and_abort_clears_it(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    spi = SpiDriver(dut)

    await spi.transfer32(isa.abort(0).encode())
    await spi.transfer32(isa.rd(0, 0).encode())
    rd_rsp = await spi.transfer32(isa.nop().encode())

    await spi.transfer32(isa.abort(0).encode())
    clear_rsp = await status_response(spi, 0)

    assert (rd_rsp >> 24) == 0xA0
    assert ((rd_rsp >> 16) & 0x80) != 0
    assert (rd_rsp & 0xFF) == 0
    assert (clear_rsp >> 24) == 0xA0
    assert ((clear_rsp >> 16) & 0x80) == 0


@cocotb.test()
async def spi_stream_dot_and_mac_int4_accumulate_signed_rows(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    spi = SpiDriver(dut)

    ch = 0
    precision = isa.Precision.INT4
    row_pairs = [
        ([3, -2], [-1, 4]),
        ([-1, 2], [5, -3]),
    ]
    expected_dot = sum(
        sum(a * b for a, b in zip(a_lanes, b_lanes)) for a_lanes, b_lanes in row_pairs
    )

    await spi.transfer32(isa.abort(ch).encode())
    await spi.transfer32(isa.config_auto_refresh(ch, False).encode())
    await write_packed_rows(
        spi,
        ch,
        0,
        [pack_lanes(a_lanes, precision) for a_lanes, _ in row_pairs],
    )
    await write_packed_rows(
        spi,
        ch,
        1,
        [pack_lanes(b_lanes, precision) for _, b_lanes in row_pairs],
    )

    await spi.transfer32(isa.stream(ch, isa.Reduce.DOT, precision, 0, 1, 0, 0, 2).encode())
    await wait_core_clocks(dut, 80)
    dot_acc = await read_acc18(spi, ch)

    await spi.transfer32(isa.stream(ch, isa.Reduce.MAC, precision, 0, 1, 0, 0, 2).encode())
    await wait_core_clocks(dut, 80)
    mac_acc = await read_acc18(spi, ch)

    assert dot_acc == expected_dot
    assert mac_acc == expected_dot * 2


@cocotb.test(skip=GATE_LEVEL)
async def spi_second_queued_command_while_busy_sets_sticky_error(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    spi = SpiDriver(dut)

    ch = 0
    precision = isa.Precision.INT2
    rows = [pack_lanes([1, -1, 0, 1], precision)] * 2

    await spi.transfer32(isa.abort(ch).encode())
    await spi.transfer32(isa.config_auto_refresh(ch, False).encode())
    await write_packed_rows(spi, ch, 0, rows)
    await write_packed_rows(spi, ch, 1, rows)
    await spi.transfer32(isa.stream(ch, isa.Reduce.DOT, precision, 0, 1, 0, 0, 2).encode())

    await RisingEdge(dut.clk)
    design = user_design(dut)
    design.cmd_word.value = Force(isa.status(ch).encode())
    design.cmd_valid.value = Force(1)
    await RisingEdge(dut.clk)
    design.cmd_word.value = Force(isa.status(ch).encode())
    design.cmd_valid.value = Force(1)
    await RisingEdge(dut.clk)
    design.cmd_valid.value = Release()
    design.cmd_word.value = Release()

    await wait_core_clocks(dut, 220)
    rsp = await status_response(spi, ch)

    assert (rsp >> 24) == 0xA0
    assert ((rsp >> 16) & 0x80) != 0
