"""Time on air, ALOHA loss and the cell-capacity model; the analytical model against Monte Carlo."""
import math

import pytest

from rakshasutra import capacity, lora, simulate


@pytest.mark.parametrize("app_bytes,symbols,ms", [(15, 53, 66.82), (64, 123, 138.50), (200, 318, 338.18)])
def test_time_on_air_matches_the_white_paper(app_bytes, symbols, ms):
    assert lora.payload_symbols(app_bytes + 13) == symbols
    assert round(lora.time_on_air(app_bytes) * 1000, 2) == ms


def test_time_on_air_grows_with_spreading_factor_and_size():
    assert lora.time_on_air(15, sf=9) > 3 * lora.time_on_air(15, sf=7)
    assert all(lora.time_on_air(b + 1) >= lora.time_on_air(b) for b in range(0, 222))


def test_low_data_rate_optimisation_only_from_sf11():
    assert lora.payload_symbols(30, sf=10) == lora.payload_symbols(30, sf=10, low_dr_opt=False)
    assert lora.payload_symbols(30, sf=11) == lora.payload_symbols(30, sf=11, low_dr_opt=True)


def test_aloha_loss():
    assert lora.aloha_loss(0) == 0
    assert round(lora.aloha_loss(0.39), 3) == 0.542          # the paper's own example: G = 39%
    one = lora.mixed_aloha_loss([(10.0, 0.1)], channels=8)[0]
    assert math.isclose(one, lora.aloha_loss(10 * 0.1 / 8))  # equal frames: reduces to 1 - exp(-2G)


def test_long_frames_are_lost_more_often_than_short_ones():
    short, long_ = lora.mixed_aloha_loss([(5.0, 0.06), (5.0, 0.34)])
    assert long_ > short


def test_chunks_never_exceed_the_payload_limit():
    for k in range(0, 400):
        frames = capacity._split(k, 25, 8)
        assert sum(frames) == 8 * k and all(0 < b <= 200 for b in frames)


def test_poisson_sums_to_one():
    for mean in (0.1, 2.27, 13.6, 50.0):
        pmf = capacity._poisson(mean)
        assert math.isclose(sum(pmf), 1.0, abs_tol=1e-9)
        assert math.isclose(sum(k * p for k, p in enumerate(pmf)), mean, rel_tol=1e-6)


def test_headline_capacity_numbers_are_pinned():
    t = capacity.table()
    got = {a: [(round(c.load * 100, 1), round(c.loss * 100, 1)) for c in rows] for a, rows in t.items()}
    assert got["single"][3] == (42.9, 57.6)
    assert got["batch"][3] == (14.6, 25.3)
    assert got["rakshasutra"][0] == (7.7, 14.3)
    assert got["rakshasutra"][3] == (18.2, 30.5)
    nd = capacity.cell_load("rakshasutra", 3000, departures=False)
    assert (round(nd.load * 100, 1), round(nd.loss * 100, 1)) == (12.0, 21.3)


def test_load_is_ordered_as_the_design_argues():
    for n in (1000, 2000, 3000):
        raw, single, batch, rak = (capacity.cell_load(a, n).load for a in capacity.ARCHITECTURES)
        assert raw > single > batch
        assert single > rak
        assert capacity.cell_load("rakshasutra", n, departures=False).load < rak


def test_only_the_bloom_design_keeps_every_frame_under_the_limit():
    assert capacity.cell_load("rakshasutra", 3000).oversize_probability == 0
    assert capacity.cell_load("rakshasutra", 3000).max_frame_bytes == 200
    assert capacity.cell_load("batch", 3000).oversize_probability > 0.1     # raw ID list over 55 wearables


def test_unknown_architecture_is_an_error():
    with pytest.raises(ValueError):
        capacity.cell_load("magic", 100)


@pytest.mark.parametrize("arch,tags", [("single", 3000), ("batch", 3000), ("rakshasutra", 500), ("rakshasutra", 3000)])
def test_monte_carlo_agrees_with_the_formula(arch, tags):
    sim = simulate.simulate_cell(arch, tags, seconds=1200, seed=3)
    model = capacity.cell_load(arch, tags)
    assert abs(sim["load"] - model.load) < 0.01
    assert abs(sim["loss"] - model.loss) < 0.03


def test_simulation_is_deterministic_for_a_seed():
    a = simulate.simulate_cell("rakshasutra", 1000, seconds=300, seed=5)
    assert a == simulate.simulate_cell("rakshasutra", 1000, seconds=300, seed=5)
