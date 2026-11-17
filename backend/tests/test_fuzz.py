"""Losowe scenariusze „wszystko ze wszystkim” – brak wyjątków, wartości skończone, brak przelewania ponad pojemność."""
import pytest

from fuzz_scenarios import run


@pytest.mark.parametrize("seed", range(40))
def test_random_scenario(seed):
    res = run(10_000 + seed)
    assert res is None, res[:2]
