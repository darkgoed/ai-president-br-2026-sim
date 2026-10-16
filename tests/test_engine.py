import pytest
import numpy as np


def test_debt_identity_uses_nominal_rates_and_primary_surplus():
    from src.engine import debt_step
    assert debt_step(0.8, 0.1, 0.05, 0.02) == pytest.approx(0.8 * 1.1 / 1.05 - 0.02)
    assert debt_step(0.8, 0, 0, 0.02) == pytest.approx(0.78)


def test_paired_reference_preserves_unknown_government_outcomes():
    from src.engine import simulate, load_inputs
    config, profiles = load_inputs()
    result = simulate(config, profiles, runs=1000, seed=20261015)
    assert result['counts']['unique_reference_trajectories'] == 1000
    assert result['counts']['profile_scenario_evaluations'] == 12000
    assert result['counts']['identified_government_effects'] == 0
    assert set(result['reference']['scenario_counts'].values()) == {125}
    assert result['ranking'] is None
    assert result['candidate_comparison_identified'] is False
    assert len(result['profiles']) == 12
    for row in result['profiles']:
        assert all(value is None for value in row['outcomes'].values())
    assert len(result['reference']['trajectories']) == 1000
    assert result == simulate(config, profiles, runs=1000, seed=20261015)
