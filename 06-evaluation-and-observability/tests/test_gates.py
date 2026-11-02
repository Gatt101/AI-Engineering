from copy import deepcopy

from research_evaluation.__main__ import evaluate, gate


def test_regression_suite_and_deliberate_citation_regression():
    report = evaluate()
    assert report["passed"], report["gates"]
    broken = deepcopy(report)
    broken["retrieval"]["summary"]["citation_validity_rate"] = 0.9
    assert not all(gate(broken).values())
    assert not gate(broken)["citation_validity"]
