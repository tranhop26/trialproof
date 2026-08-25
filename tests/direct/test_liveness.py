import json

import pytest

from test_consensus import mock_sources, resolution
from test_registry import warp


START = 1_800_000_000


@pytest.fixture
def contract(direct_vm, direct_deploy):
    warp(direct_vm, START)
    return direct_deploy("contracts/trial_proof.py")


def register(contract, direct_vm, sender, nct_id="NCT01234567"):
    direct_vm.sender = sender
    return json.loads(contract.register_study(nct_id))["assessment_id"]


def action_required(contract, direct_vm, assessment_id, caller):
    mock_sources(direct_vm)
    direct_vm.mock_llm(
        ".*",
        json.dumps(
            resolution(
                verdict="ACTION_REQUIRED",
                reason_codes=["MISSING_PRIMARY_RESULT"],
                matched_registered_indices=[0],
                missing_registered_indices=[1],
            )
        ),
    )
    direct_vm.sender = caller
    contract.assess(assessment_id)


def test_unrelated_address_can_expire_at_exact_deadline(
    contract, direct_vm, direct_alice, direct_charlie
):
    assessment_id = register(contract, direct_vm, direct_alice)
    stored = json.loads(contract.get_assessment(assessment_id))
    direct_vm.sender = direct_charlie
    warp(direct_vm, stored["assessment_deadline"] - 1)
    with direct_vm.expect_revert("ASSESSMENT_NOT_EXPIRED"):
        contract.expire_assessment(assessment_id)

    warp(direct_vm, stored["assessment_deadline"])
    receipt = json.loads(contract.expire_assessment(assessment_id))
    readback = json.loads(contract.get_assessment(assessment_id))
    assert receipt["state"] == "UNRESOLVED"
    assert readback["certified"] is False
    assert readback["resolution"]["reason_codes"] == ["CONSENSUS_OR_EXECUTION_TIMEOUT"]


def test_refresh_is_permissionless_and_enforces_exact_cooldown(
    contract, direct_vm, direct_alice, direct_charlie
):
    assessment_id = register(contract, direct_vm, direct_alice)
    action_required(contract, direct_vm, assessment_id, direct_charlie)
    stored = json.loads(contract.get_assessment(assessment_id))
    direct_vm.clear_mocks()
    mock_sources(direct_vm)
    direct_vm.mock_llm(".*", json.dumps(resolution()))
    direct_vm.sender = direct_alice

    warp(direct_vm, stored["next_refresh_at"] - 1)
    with direct_vm.expect_revert("REFRESH_NOT_READY"):
        contract.refresh(assessment_id)

    warp(direct_vm, stored["next_refresh_at"])
    receipt = json.loads(contract.refresh(assessment_id))
    readback = json.loads(contract.get_assessment(assessment_id))
    assert receipt["state"] == "DISCLOSURE_COMPLETE"
    assert readback["attempt"] == 2
    assert readback["revision"] == 2
    assert readback["certified"] is True


def test_max_attempts_close_without_certification(
    contract, direct_vm, direct_alice, direct_charlie
):
    assessment_id = register(contract, direct_vm, direct_alice)
    action_required(contract, direct_vm, assessment_id, direct_charlie)
    for expected_attempt in [2, 3]:
        stored = json.loads(contract.get_assessment(assessment_id))
        warp(direct_vm, stored["next_refresh_at"])
        direct_vm.clear_mocks()
        mock_sources(direct_vm)
        direct_vm.mock_llm(
            ".*",
            json.dumps(
                resolution(
                    verdict="ACTION_REQUIRED",
                    reason_codes=["MISSING_PRIMARY_RESULT"],
                    matched_registered_indices=[0],
                    missing_registered_indices=[1],
                )
            ),
        )
        direct_vm.sender = direct_charlie
        contract.refresh(assessment_id)
        assert (
            json.loads(contract.get_assessment(assessment_id))["attempt"]
            == expected_attempt
        )

    before = contract.get_assessment(assessment_id)
    with direct_vm.expect_revert("MAX_ATTEMPTS_REACHED"):
        contract.refresh(assessment_id)
    assert contract.get_assessment(assessment_id) == before

    receipt = json.loads(contract.close_after_max_attempts(assessment_id))
    assert receipt["state"] == "CLOSED_UNCERTIFIED"
    assert json.loads(contract.get_assessment(assessment_id))["certified"] is False
    with direct_vm.expect_revert("INVALID_STATE"):
        contract.close_after_max_attempts(assessment_id)


def test_terminal_certification_rejects_every_followup(
    contract, direct_vm, direct_alice, direct_charlie
):
    assessment_id = register(contract, direct_vm, direct_alice)
    mock_sources(direct_vm)
    direct_vm.mock_llm(".*", json.dumps(resolution()))
    direct_vm.sender = direct_charlie
    contract.assess(assessment_id)
    before = contract.get_assessment(assessment_id)

    for method in [
        contract.assess,
        contract.refresh,
        contract.expire_assessment,
        contract.close_after_max_attempts,
    ]:
        with direct_vm.expect_revert("INVALID_STATE"):
            method(assessment_id)
        assert contract.get_assessment(assessment_id) == before


def test_close_rejects_before_max_attempts(
    contract, direct_vm, direct_alice, direct_charlie
):
    assessment_id = register(contract, direct_vm, direct_alice)
    action_required(contract, direct_vm, assessment_id, direct_charlie)
    with direct_vm.expect_revert("MAX_ATTEMPTS_NOT_REACHED"):
        contract.close_after_max_attempts(assessment_id)
