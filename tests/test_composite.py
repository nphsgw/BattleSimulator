import battlesim as bsm


def test_composite_preserves_explicit_army_configuration():
    """Model-contract inputs must survive conversion to the domain object."""
    composite = bsm.Composite(
        "example1",
        2,
        init_ai="weakest",
        rolling_ai="highest_threat",
        decision_ai="hit_and_run",
        doctrine_weights=(0.1, 0.2, 0.3, 0.4),
        initial_positions=((1.0, 2.0), (3.0, 4.0)),
    )

    assert composite.name == "example1"
    assert composite.n == 2
    assert composite.init_ai == "weakest"
    assert composite.rolling_ai == "highest_threat"
    assert composite.decision_ai == "hit_and_run"
    assert composite.doctrine_weights == (0.1, 0.2, 0.3, 0.4)
    assert composite.initial_positions == ((1.0, 2.0), (3.0, 4.0))
