"""Dense-layer inference demo using the Tiny DRAM-PIM controller model.

The hardware DOT command has one precision field, so mixed activation/weight
precision is emulated by promoting each dot-product chunk to the wider lane
precision. This keeps arithmetic exact for the supplied quantized values, but
the memory packing density follows the wider operand.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test.model import isa
from test.model.pim_model import ROWS_PER_BANK, TinyPimModel


PRECISION_BITS = {
    isa.Precision.INT1: 1,
    isa.Precision.INT2: 2,
    isa.Precision.INT4: 4,
    isa.Precision.INT8: 8,
}


@dataclass(frozen=True)
class DenseRun:
    outputs: list[int]
    activation_precision: isa.Precision
    weight_precision: isa.Precision
    execution_precision: isa.Precision
    lanes_per_row: int
    chunks_per_output: int


def reference_dense(
    activations: Sequence[int],
    weights: Sequence[Sequence[int]],
    bias: Sequence[int] | None = None,
) -> list[int]:
    """Pure Python dense layer: output_j = dot(activations, weights_j) + bias_j."""

    _validate_matrix(activations, weights, bias)
    bias_values = [0] * len(weights) if bias is None else list(bias)
    return [
        sum(a * w for a, w in zip(activations, output_weights)) + bias_values[out_idx]
        for out_idx, output_weights in enumerate(weights)
    ]


def run_dense_layer(
    activations: Sequence[int],
    weights: Sequence[Sequence[int]],
    activation_precision: isa.Precision,
    weight_precision: isa.Precision,
    bias: Sequence[int] | None = None,
    *,
    model: TinyPimModel | None = None,
    ch: int = 0,
) -> DenseRun:
    """Run a quantized dense layer through the PIM model's STREAM.DOT path.

    `weights` is indexed as `[output][input]`. INT1 is treated as unsigned
    0/1 data, matching the RTL DOT semantics. INT2/INT4/INT8 are signed
    two's-complement lanes.
    """

    _validate_matrix(activations, weights, bias)
    _validate_values(activations, activation_precision, "activation")
    for output_weights in weights:
        _validate_values(output_weights, weight_precision, "weight")

    pim = TinyPimModel() if model is None else model
    exec_precision = _execution_precision(activation_precision, weight_precision)
    lanes_per_row = 8 // PRECISION_BITS[exec_precision]
    values_per_chunk = lanes_per_row * ROWS_PER_BANK
    bias_values = [0] * len(weights) if bias is None else list(bias)

    outputs: list[int] = []
    max_chunks = 0
    for output_idx, output_weights in enumerate(weights):
        total = bias_values[output_idx]
        chunks = 0
        for start in range(0, len(activations), values_per_chunk):
            a_chunk = list(activations[start : start + values_per_chunk])
            w_chunk = list(output_weights[start : start + values_per_chunk])
            total += _run_dot_chunk(pim, ch, a_chunk, w_chunk, exec_precision)
            chunks += 1
        outputs.append(total)
        max_chunks = max(max_chunks, chunks)

    return DenseRun(
        outputs=outputs,
        activation_precision=activation_precision,
        weight_precision=weight_precision,
        execution_precision=exec_precision,
        lanes_per_row=lanes_per_row,
        chunks_per_output=max_chunks,
    )


def _run_dot_chunk(
    model: TinyPimModel,
    ch: int,
    activations: Sequence[int],
    weights: Sequence[int],
    precision: isa.Precision,
) -> int:
    lanes_per_row = 8 // PRECISION_BITS[precision]
    rows_needed = (len(activations) + lanes_per_row - 1) // lanes_per_row
    padded_len = rows_needed * lanes_per_row
    a_values = list(activations) + [0] * (padded_len - len(activations))
    w_values = list(weights) + [0] * (padded_len - len(weights))

    if rows_needed < 1 or rows_needed > ROWS_PER_BANK:
        raise ValueError(f"dot chunk must use between 1 and {ROWS_PER_BANK} rows")

    model.execute(isa.abort(ch))
    model.execute(isa.config_auto_refresh(ch, False))
    for row in range(rows_needed):
        a_row = _pack_lanes(a_values[row * lanes_per_row : (row + 1) * lanes_per_row], precision)
        w_row = _pack_lanes(w_values[row * lanes_per_row : (row + 1) * lanes_per_row], precision)
        model.execute(isa.act(ch, 0, row))
        model.execute(isa.wr(ch, 0, a_row))
        model.execute(isa.act(ch, 1, row))
        model.execute(isa.wr(ch, 1, w_row))

    model.execute(isa.stream(ch, isa.Reduce.DOT, precision, 0, 1, 0, 0, rows_needed))
    acc0 = model.execute(isa.acc(ch, 0)) or 0
    acc1 = model.execute(isa.acc(ch, 1)) or 0
    acc2 = model.execute(isa.acc(ch, 2)) or 0
    return _sign_extend(acc0 | (acc1 << 8) | ((acc2 & 0x03) << 16), 18)


def _pack_lanes(values: Sequence[int], precision: isa.Precision) -> int:
    if precision == isa.Precision.INT1:
        packed = 0
        for idx, value in enumerate(values):
            if value not in (0, 1):
                raise ValueError(f"INT1 lane {idx} must be 0 or 1")
            packed |= value << idx
        return packed & 0xFF

    bits = PRECISION_BITS[precision]
    mask = (1 << bits) - 1
    packed = 0
    for idx, value in enumerate(values):
        _validate_signed_value(value, bits, f"lane {idx}")
        packed |= (value & mask) << (idx * bits)
    return packed & 0xFF


def _execution_precision(
    activation_precision: isa.Precision,
    weight_precision: isa.Precision,
) -> isa.Precision:
    return max(activation_precision, weight_precision, key=lambda precision: PRECISION_BITS[precision])


def _validate_matrix(
    activations: Sequence[int],
    weights: Sequence[Sequence[int]],
    bias: Sequence[int] | None,
) -> None:
    if not activations:
        raise ValueError("activations must not be empty")
    if not weights:
        raise ValueError("weights must contain at least one output row")
    for idx, output_weights in enumerate(weights):
        if len(output_weights) != len(activations):
            raise ValueError(f"weight row {idx} length must match activations")
    if bias is not None and len(bias) != len(weights):
        raise ValueError("bias length must match number of output rows")


def _validate_values(values: Sequence[int], precision: isa.Precision, name: str) -> None:
    if precision == isa.Precision.INT1:
        for idx, value in enumerate(values):
            if value not in (0, 1):
                raise ValueError(f"{name} INT1 value {idx} must be 0 or 1")
        return

    bits = PRECISION_BITS[precision]
    for idx, value in enumerate(values):
        _validate_signed_value(value, bits, f"{name} value {idx}")


def _validate_signed_value(value: int, bits: int, name: str) -> None:
    low = -(1 << (bits - 1))
    high = (1 << (bits - 1)) - 1
    if value < low or value > high:
        raise ValueError(f"{name}={value} outside signed INT{bits} range [{low}, {high}]")


def _sign_extend(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def main() -> None:
    activations = [1, -2, 3, 0, -1, 2, 1, -3, 2, 0]
    weights = [
        [1, -1, 1, 0, -2, 1, 0, 1, -1, 1],
        [-1, 0, 1, -2, 1, 1, -1, 0, 1, -1],
    ]
    bias = [1, -2]
    result = run_dense_layer(
        activations,
        weights,
        activation_precision=isa.Precision.INT4,
        weight_precision=isa.Precision.INT2,
        bias=bias,
    )

    print("dense outputs:", result.outputs)
    print("reference:", reference_dense(activations, weights, bias))
    print(
        "execution:",
        result.execution_precision.name,
        f"{result.lanes_per_row} lanes/row",
        f"{result.chunks_per_output} chunk(s)/output",
    )


if __name__ == "__main__":
    main()
