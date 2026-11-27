"""A seed is the whole source of variation. The clock is not."""

from qa_data_factory import OrderGraphFactory


def _build(seed: int):
    return OrderGraphFactory(seed=seed).build(
        customers=3,
        orders_per_customer=2,
        lines_per_order=2,
    )


def test_same_seed_is_identical_across_calls():
    assert _build(42) == _build(42)


def test_same_seed_does_not_depend_on_a_previous_build():
    _build(7)
    assert _build(42) == _build(42)


def test_different_seeds_differ():
    assert _build(42) != _build(43)


def test_factory_seed_argument_overrides_config_seed():
    from qa_data_factory import FactoryConfig

    config = FactoryConfig(seed=1, customers=2, orders_per_customer=1, lines_per_order=1)
    from_config = OrderGraphFactory(config=config).build()
    overridden = OrderGraphFactory(seed=99, config=config).build()
    assert from_config.seed == 1
    assert overridden.seed == 99
    assert from_config != overridden
