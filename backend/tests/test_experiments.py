import pytest

from app.experiments import REGISTRY, check_expectations


@pytest.mark.parametrize("eid", sorted(REGISTRY))
def test_experiment(eid):
    failures, events, views = check_expectations(eid)
    assert not failures, f"{eid}: {failures}\n" + "\n".join(e["text"] for e in events[-25:])
