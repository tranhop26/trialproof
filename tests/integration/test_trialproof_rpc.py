import json
from datetime import datetime, timezone

import pytest
from gltest import get_contract_factory, get_validator_factory
from gltest.assertions import tx_execution_succeeded
from gltest.contracts import Contract
from gltest.types import TransactionStatus
from gltest.utils import extract_contract_address


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
NCT_ID = "NCT01234567"
VERSION_URL = "https://clinicaltrials.gov/api/v2/version"
FIELDS = "NCTId,LeadSponsorName,OverallStatus,PrimaryCompletionDate,ResultsFirstPostDate,PrimaryOutcomeMeasure,PrimaryOutcomeDescription,PrimaryOutcomeTimeFrame,HasResults,OutcomeMeasureType,OutcomeMeasureTitle,OutcomeMeasureDescription,OutcomeMeasurementValue"
STUDY_URL = (
    f"https://clinicaltrials.gov/api/v2/studies/{NCT_ID}?format=json&fields={FIELDS}"
)


def _iso(timestamp: int) -> str:
    return (
        datetime.fromtimestamp(timestamp, timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _study() -> dict:
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": NCT_ID,
            },
            "sponsorCollaboratorsModule": {
                "leadSponsor": {"name": "Example Research Institute"}
            },
            "statusModule": {
                "overallStatus": "COMPLETED",
                "primaryCompletionDateStruct": {"date": "2025-01-01", "type": "ACTUAL"},
                "resultsFirstPostDateStruct": {"date": "2025-10-01", "type": "ACTUAL"},
            },
            "outcomesModule": {
                "primaryOutcomes": [
                    {
                        "measure": "Change in systolic blood pressure",
                        "description": "Mean change from baseline",
                        "timeFrame": "Week 12",
                    },
                    {
                        "measure": "Serious adverse events",
                        "description": "Participants with an SAE",
                        "timeFrame": "Through week 12",
                    },
                ]
            },
        },
        "resultsSection": {
            "outcomeMeasuresModule": {
                "outcomeMeasures": [
                    {
                        "type": "PRIMARY",
                        "title": "Systolic blood pressure change at week 12",
                        "description": "Change from baseline",
                        "classes": [
                            {"categories": [{"measurements": [{"value": "-8.2"}]}]}
                        ],
                    },
                    {
                        "type": "PRIMARY",
                        "title": "Number of participants with serious adverse events",
                        "description": "SAE count through week 12",
                        "classes": [
                            {"categories": [{"measurements": [{"value": "3"}]}]}
                        ],
                    },
                ]
            }
        },
        "hasResults": True,
    }


def _resolution() -> dict:
    return {
        "verdict": "DISCLOSURE_COMPLETE",
        "nct_id": NCT_ID,
        "sponsor_identity": "example research institute",
        "reason_codes": [],
        "registered_primary_count": 2,
        "reported_outcome_count": 2,
        "matched_registered_indices": [0, 1],
        "missing_registered_indices": [],
        "source_safe": True,
        "source_fresh": True,
        "rationale": "Both registered primary outcomes have reported data.",
    }


def _mock_context(timestamp: int) -> dict:
    validators = get_validator_factory().batch_create_mock_validators(
        count=5,
        mock_llm_response={
            "nondet_exec_prompt": {"trialproof-disclosure/1": json.dumps(_resolution())}
        },
        mock_web_response={
            "nondet_web_request": {
                VERSION_URL: {
                    "method": "GET",
                    "status": 200,
                    "body": json.dumps(
                        {
                            "apiVersion": "2.0.1",
                            "dataTimestamp": _iso(timestamp).removesuffix("Z"),
                        }
                    ),
                },
                STUDY_URL: {
                    "method": "GET",
                    "status": 200,
                    "body": json.dumps(_study()),
                },
            }
        },
    )
    return {
        "validators": [validator.to_dict() for validator in validators],
        "genvm_datetime": _iso(timestamp),
    }


def _schema_methods(schema: dict | None) -> set[str]:
    return set((schema or {}).get("methods", {}))


def _skip_if_rpc_unavailable(exc: Exception) -> None:
    if any(
        signal in str(exc)
        for signal in [
            "Connection refused",
            "Request to",
            "timed out",
            "Max retries exceeded",
            "Failed to establish a new connection",
        ]
    ):
        pytest.skip("TRIALPROOF_RPC_UNAVAILABLE")


@pytest.fixture(scope="session")
def rpc_roles(gl_client, accounts):
    try:
        gl_client.get_block_number()
    except Exception as exc:
        _skip_if_rpc_unavailable(exc)
        raise
    if len(accounts) < 2:
        pytest.skip("TRIALPROOF_TWO_RPC_ACCOUNTS_REQUIRED")
    assert str(accounts[0].address).lower() != str(accounts[1].address).lower()
    return {"registrant": accounts[0], "resolver": accounts[1]}


@pytest.fixture(scope="session")
def contract_factory(rpc_roles):
    return get_contract_factory(contract_file_path="../deploy/source/trial_proof.py")


def test_mock_context_has_five_validators_and_bound_sources():
    context = _mock_context(1_800_000_000)
    assert len(context["validators"]) == 5
    serialized = json.dumps(context)
    assert NCT_ID in serialized
    assert VERSION_URL in serialized
    assert "DISCLOSURE_COMPLETE" in serialized


def test_expected_schema_surface_is_frozen():
    assert EXPECTED_PUBLIC_METHODS == {
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


def test_trialproof_finalized_rpc_consensus_and_readback(
    gl_client, contract_factory, rpc_roles
):
    deploy_receipt = contract_factory.deploy_contract_tx(
        account=rpc_roles["registrant"],
        wait_transaction_status=TransactionStatus.FINALIZED,
    )
    assert tx_execution_succeeded(deploy_receipt)
    address = extract_contract_address(deploy_receipt)
    code_schema = gl_client.get_contract_schema_for_code(contract_factory.contract_code)
    runtime_schema = gl_client.get_contract_schema(address)
    assert _schema_methods(code_schema) == EXPECTED_PUBLIC_METHODS
    assert _schema_methods(runtime_schema) == EXPECTED_PUBLIC_METHODS
    contract = Contract.new(
        address=address, schema=runtime_schema, account=rpc_roles["registrant"]
    )

    registered = contract.register_study(args=[NCT_ID]).transact(
        wait_transaction_status=TransactionStatus.FINALIZED,
        transaction_context={"genvm_datetime": _iso(1_800_000_000)},
    )
    assert tx_execution_succeeded(registered)
    assessment_id = json.loads(
        registered["consensus_data"]["leader_receipt"][0]["result"]
    )["assessment_id"]

    assessed = (
        contract.connect(rpc_roles["resolver"])
        .assess(args=[assessment_id])
        .transact(
            wait_transaction_status=TransactionStatus.FINALIZED,
            transaction_context=_mock_context(1_800_000_000),
        )
    )
    assert tx_execution_succeeded(assessed)
    readback = json.loads(contract.get_assessment(args=[assessment_id]).call())
    assert readback["state"] == "DISCLOSURE_COMPLETE"
    assert readback["certified"] is True
    assert readback["attempt"] == 1
