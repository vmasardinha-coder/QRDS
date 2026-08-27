from tools.gate_btc_factory.frontier_workflow_repair import classify


def run(**overrides):
    base = {
        "status": "completed",
        "conclusion": "failure",
        "run_attempt": 1,
    }
    base.update(overrides)
    return base


def test_retries_operational_source_failure_once():
    action, _ = classify(run(), ["Probe official BCB Focus OData source"])
    assert action == "RETRY_FAILED_JOBS_ONCE"


def test_second_failure_becomes_persistent_blocker():
    action, _ = classify(run(run_attempt=2), ["Probe official BCB Focus OData source"])
    assert action == "PERSISTENT_BLOCKER"


def test_scientific_failure_fails_closed():
    action, _ = classify(run(), ["Replication result survivor promotion"])
    assert action == "FAIL_CLOSED_SCIENCE"


def test_unclassified_failure_is_not_retried():
    action, _ = classify(run(), ["Compute result"])
    assert action == "PERSISTENT_BLOCKER"


def test_active_run_respects_single_flight():
    action, _ = classify(run(status="in_progress", conclusion=None), [])
    assert action == "ACTIVE"
