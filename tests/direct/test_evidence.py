import copy
import json

import pytest

from test_registry import warp


OBSERVED_AT = 1_800_000_000


@pytest.fixture
def contract(direct_vm, direct_deploy):
    warp(direct_vm, OBSERVED_AT)
    return direct_deploy("contracts/trial_proof.py")


@pytest.fixture
def fresh_version():
    return {"apiVersion": "2.0.1", "dataTimestamp": "2027-01-15T08:00:00"}


@pytest.fixture
def complete_study():
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT01234567",
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
        "derivedSection": {"miscInfoModule": {"versionHolder": "2027-01-15"}},
    }


def test_contract_constructs_only_official_urls(contract):
    assert contract._version_url() == "https://clinicaltrials.gov/api/v2/version"
    study_url = contract._study_url("NCT01234567")
    assert study_url.startswith(
        "https://clinicaltrials.gov/api/v2/studies/NCT01234567?"
    )
    assert "format=json" in study_url
    assert "fields=" in study_url
    assert "OutcomeMeasureType" in study_url
    assert "OutcomeType" not in study_url
    assert "http://" not in study_url


def test_identity_mismatch_is_unsafe(contract, fresh_version, complete_study):
    changed = copy.deepcopy(complete_study)
    changed["protocolSection"]["identificationModule"]["nctId"] = "NCT76543210"
    result = contract._extract_source_snapshot(
        fresh_version, changed, "NCT01234567", OBSERVED_AT
    )
    assert result["safe"] is False
    assert result["verdict"] == "UNRESOLVED"
    assert result["failure_code"] == "SOURCE_IDENTITY_MISMATCH"


def test_stale_future_or_malformed_version_is_unsafe(contract, complete_study):
    cases = [
        (
            {"apiVersion": "2.0.1", "dataTimestamp": "2027-01-10T07:59:59"},
            "SOURCE_STALE",
        ),
        (
            {"apiVersion": "2.0.1", "dataTimestamp": "2027-01-15T08:05:01"},
            "SOURCE_FUTURE",
        ),
        (
            {"apiVersion": "2.0.1", "dataTimestamp": "not-a-date"},
            "SOURCE_VERSION_MALFORMED",
        ),
        ({"dataTimestamp": "2027-01-15T08:00:00"}, "SOURCE_VERSION_MALFORMED"),
    ]
    for version, expected_code in cases:
        result = contract._extract_source_snapshot(
            version, complete_study, "NCT01234567", OBSERVED_AT
        )
        assert result["safe"] is False
        assert result["verdict"] == "UNRESOLVED"
        assert result["failure_code"] == expected_code


def test_missing_decision_fields_request_more_info(
    contract, fresh_version, complete_study
):
    changed = copy.deepcopy(complete_study)
    del changed["protocolSection"]["outcomesModule"]["primaryOutcomes"]
    result = contract._extract_source_snapshot(
        fresh_version, changed, "NCT01234567", OBSERVED_AT
    )
    assert result["safe"] is True
    assert result["preliminary"] == "REQUEST_MORE_INFO"
    assert result["failure_code"] == "PRIMARY_OUTCOMES_MISSING"


def test_complete_snapshot_binds_source_subject_time_and_sponsor(
    contract, fresh_version, complete_study
):
    result = contract._extract_source_snapshot(
        fresh_version, complete_study, "NCT01234567", OBSERVED_AT
    )
    assert result["safe"] is True
    assert result["preliminary"] == "READY_FOR_SEMANTIC_REVIEW"
    assert result["nct_id"] == "NCT01234567"
    assert result["sponsor_identity"] == "example research institute"
    assert result["api_version"] == "2.0.1"
    assert result["api_data_timestamp"] == 1_800_000_000
    assert result["observed_at"] == OBSERVED_AT
    assert len(result["registered_primary_outcomes"]) == 2
    assert len(result["reported_outcomes"]) == 2


def test_snapshot_hash_is_canonical_and_action_domain_separates_attempts(
    contract, direct_vm, direct_alice, fresh_version, complete_study
):
    snapshot = contract._extract_source_snapshot(
        fresh_version, complete_study, "NCT01234567", OBSERVED_AT
    )
    evidence_hash = contract._hash_snapshot(snapshot)
    assert evidence_hash.startswith("0x") and len(evidence_hash) == 66
    reordered = json.loads(json.dumps(snapshot, sort_keys=False))
    assert contract._hash_snapshot(reordered) == evidence_hash

    direct_vm.sender = direct_alice
    assessment_id = json.loads(contract.register_study("NCT01234567"))["assessment_id"]
    assessment = json.loads(contract.get_assessment(assessment_id))
    first = contract._action_domain(
        assessment_id, assessment, evidence_hash, "ASSESS", 1, 1
    )
    retry = contract._action_domain(
        assessment_id, assessment, evidence_hash, "REFRESH", 2, 2
    )
    assert first != retry
    assert len(first) == 66 and len(retry) == 66


def test_fetch_json_rejects_transport_and_size_failures(contract, monkeypatch):
    class Response:
        def __init__(self, status, body):
            self.status_code = status
            self.body = body

    monkeypatch.setattr(gl_web(contract), "get", lambda _url: Response(503, b"{}"))
    assert (
        contract._fetch_json(contract._version_url())["failure_code"]
        == "SOURCE_HTTP_ERROR"
    )

    monkeypatch.setattr(
        gl_web(contract), "get", lambda _url: Response(200, b"x" * 24_577)
    )
    assert (
        contract._fetch_json(contract._version_url())["failure_code"]
        == "SOURCE_TOO_LARGE"
    )

    monkeypatch.setattr(
        gl_web(contract), "get", lambda _url: Response(200, b"not-json")
    )
    assert (
        contract._fetch_json(contract._version_url())["failure_code"]
        == "SOURCE_MALFORMED"
    )


def gl_web(contract):
    instance = object.__getattribute__(contract, "_instance")
    return instance.__class__.register_study.__globals__["gl"].nondet.web
