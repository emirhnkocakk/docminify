from docminify.optimizers.base import OptimizationResult


def test_reduction_calculation():
    result = OptimizationResult(
        original_size=1000,
        optimized_size=600,
    )

    assert result.reduction_bytes == 400
    assert result.reduction_percentage == 40.0


def test_zero_original_size():
    result = OptimizationResult(
        original_size=0,
        optimized_size=0,
    )

    assert result.reduction_bytes == 0
    assert result.reduction_percentage == 0.0


def test_to_dict_output():
    result = OptimizationResult(
        original_size=1000,
        optimized_size=800,
        warnings=["minor issue"],
        errors=[],
    )

    result_dict = result.to_dict()

    assert result_dict["original_size"] == 1000
    assert result_dict["optimized_size"] == 800
    assert result_dict["reduction_bytes"] == 200
    assert result_dict["reduction_percentage"] == 20.0
    assert result_dict["warnings"] == ["minor issue"]
    assert result_dict["errors"] == []