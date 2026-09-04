import pytest

from examples.dense_layer_demo import reference_dense, run_dense_layer
from test.model import isa


def test_dense_layer_int4_activation_int2_weight_matches_reference():
    activations = [1, -2, 3, 0, -1, 2, 1, -3, 2, 0]
    weights = [
        [1, -1, 1, 0, -2, 1, 0, 1, -1, 1],
        [-1, 0, 1, -2, 1, 1, -1, 0, 1, -1],
    ]
    bias = [1, -2]

    result = run_dense_layer(
        activations,
        weights,
        isa.Precision.INT4,
        isa.Precision.INT2,
        bias,
    )

    assert result.outputs == reference_dense(activations, weights, bias)
    assert result.execution_precision == isa.Precision.INT4
    assert result.lanes_per_row == 2
    assert result.chunks_per_output == 2


def test_dense_layer_int1_activation_int8_weight_promotes_execution_width():
    activations = [1, 0, 1, 1, 0]
    weights = [[-3, 7, 2, -1, 5]]

    result = run_dense_layer(
        activations,
        weights,
        isa.Precision.INT1,
        isa.Precision.INT8,
    )

    assert result.outputs == reference_dense(activations, weights)
    assert result.execution_precision == isa.Precision.INT8
    assert result.lanes_per_row == 1
    assert result.chunks_per_output == 2


def test_dense_layer_int1_int1_uses_unsigned_bit_dot_density():
    activations = [1, 0, 1, 1, 0, 0, 1, 1, 1]
    weights = [[1, 1, 0, 1, 0, 1, 1, 0, 1]]

    result = run_dense_layer(
        activations,
        weights,
        isa.Precision.INT1,
        isa.Precision.INT1,
    )

    assert result.outputs == [4]
    assert result.outputs == reference_dense(activations, weights)
    assert result.execution_precision == isa.Precision.INT1
    assert result.lanes_per_row == 8
    assert result.chunks_per_output == 1


def test_dense_layer_rejects_values_outside_declared_precision():
    with pytest.raises(ValueError, match="activation value 0"):
        run_dense_layer([2], [[1]], isa.Precision.INT2, isa.Precision.INT2)

    with pytest.raises(ValueError, match="weight INT1 value 0"):
        run_dense_layer([1], [[-1]], isa.Precision.INT1, isa.Precision.INT1)
