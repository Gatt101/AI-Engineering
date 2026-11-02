from research_service.demo import run_demo
from research_workflows.__main__ import run_demo as recovery_demo


def test_portfolio_claims_have_executable_evidence():
    assert run_demo()["api_flow"] == "passed"
    assert recovery_demo()["receipt_deduplicated"]
