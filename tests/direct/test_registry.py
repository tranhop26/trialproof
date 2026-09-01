import json
import sys
from datetime import datetime, timezone

import pytest


def warp(direct_vm, timestamp: int) -> None:
    transaction_datetime = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
    direct_vm.warp(transaction_datetime)
    gl = sys.modules.get("genlayer.gl")
    if gl is not None:
        gl.message_raw["datetime"] = transaction_datetime


@pytest.fixture
def contract(direct_vm, direct_deploy):
    warp(direct_vm, 1_800_000_000)
    return direct_deploy("contracts/trial_proof.py")


def register(contract, direct_vm, sender, nct_id="NCT01234567"):
    direct_vm.sender = sender
    return json.loads(contract.register_study(nct_id))


def test_registers_canonical_nct_and_rejects_duplicate(
    contract, direct_vm, direct_alice
):
    receipt = register(contract, direct_vm, direct_alice, "nct01234567")
    assert receipt == {
        "action": "REGISTER_STUDY",
        "assessment_id": "1",
        "state": "REGISTERED",
    }
    stored = json.loads(contract.get_assessment("1"))
    assert stored["nct_id"] == "NCT01234567"
    assert stored["registrant"] == str(direct_alice).lower()
    assert stored["certified"] is False
    assert stored["attempt"] == 0
    assert stored["revision"] == 0
    with direct_vm.expect_revert("ASSESSMENT_ALREADY_EXISTS"):
        contract.register_study("NCT01234567")


@pytest.mark.parametrize(
    "value",
    ["", "NCT123", "NCT0123456X", " NCT01234567", "NCT01234567\n"],
)
def test_rejects_noncanonical_or_ambiguous_nct_ids(
    contract, direct_vm, direct_alice, value
):
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("INVALID_NCT_ID"):
        contract.register_study(value)


def test_views_and_pagination_are_bounded(contract, direct_vm, direct_alice):
    for nct_id in ["NCT00000001", "NCT00000002", "NCT00000003"]:
        register(contract, direct_vm, direct_alice, nct_id)

    assert contract.get_assessment_count() == 3
    assert contract.get_assessment_ids_page(0, 2) == ["1", "2"]
    assert contract.get_assessment_ids_page(2, 2) == ["3"]
    assert (
        json.loads(contract.get_assessment_by_nct_id("nct00000002"))["assessment_id"]
        == "2"
    )
    assert contract.get_assessment_by_nct_id("NCT99999999") == "{}"
    with direct_vm.expect_revert("INVALID_PAGE"):
        contract.get_assessment_ids_page(-1, 1)
    with direct_vm.expect_revert("INVALID_PAGE"):
        contract.get_assessment_ids_page(0, 0)
    with direct_vm.expect_revert("INVALID_PAGE"):
        contract.get_assessment_ids_page(0, 101)


def test_unknown_assessment_reverts(contract, direct_vm):
    with direct_vm.expect_revert("ASSESSMENT_NOT_FOUND"):
        contract.get_assessment("404")


def test_version_is_fixed(contract):
    assert contract.get_version() == "trialproof/1.1.0"
