import json
import sys

import pytest

from test_registry import warp


EXPECTED_PUBLIC_METHODS = {
    "assess",
    "close_after_max_attempts",
    "expire_assessment",
    "get_assessment",
    "get_assessment_by_nct_id",
    "get_assessment_count",
    "get_assessment_ids_page",
    "get_version",
    "refresh",
    "register_study",
}


@pytest.fixture
def contract_module(direct_vm, direct_deploy):
    warp(direct_vm, 1_800_000_000)
    direct_deploy("contracts/trial_proof.py")
    return sys.modules["_contract_trial_proof"]


def test_public_schema_is_exactly_frozen(contract_module):
    schema = json.loads(contract_module.TrialProof.__get_schema__())
    assert set(schema["methods"]) == EXPECTED_PUBLIC_METHODS
    assert all(value.get("payable") is not True for value in schema["methods"].values())


def test_contract_exposes_no_privileged_recovery_or_verdict_route(contract_module):
    forbidden = {
        "admin",
        "owner",
        "pause",
        "set_policy",
        "set_source",
        "set_verdict",
        "upgrade",
        "withdraw",
    }
    schema = json.loads(contract_module.TrialProof.__get_schema__())
    public_methods = set(schema["methods"])
    assert public_methods.isdisjoint(forbidden)
