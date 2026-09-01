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


def extract(contract, fresh_version, study):
    return contract._extract_source_snapshot(
        fresh_version, study, "NCT01234567", OBSERVED_AT
    )


def without_reported_results(study):
    changed = copy.deepcopy(study)
    changed["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"] = []
    return changed


@pytest.mark.parametrize(
    "classes",
    [
        [{}],
        [{"categories": []}],
        [{"categories": [{}]}],
        [{"categories": [{"measurements": []}]}],
        [{"categories": [{"measurements": [{}]}]}],
        [{"categories": [{"measurements": [{"value": ""}]}]}],
        [{"categories": [{"measurements": [{"value": "   "}]}]}],
        [{"categories": [{"measurements": [{"value": 0}]}]}],
    ],
)
def test_non_empty_classes_without_valid_measurement_are_not_result_data(
    contract, fresh_version, complete_study, classes
):
    changed = copy.deepcopy(complete_study)
    changed["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0][
        "classes"
    ] = classes
    result = extract(contract, fresh_version, changed)
    assert len(result.get("reported_outcomes", [])) == 1
    assert all(
        outcome["title"] != "Systolic blood pressure change at week 12"
        for outcome in result["reported_outcomes"]
    )


def test_secondary_outcome_with_measurement_is_excluded(
    contract, fresh_version, complete_study
):
    changed = copy.deepcopy(complete_study)
    changed["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]["type"] = (
        "SECONDARY"
    )
    result = extract(contract, fresh_version, changed)
    assert len(result["reported_outcomes"]) == 1
    assert {item["type"] for item in result["reported_outcomes"]} == {"PRIMARY"}


@pytest.mark.parametrize("outcome_type", ["primary"])
def test_non_canonical_primary_type_is_excluded(
    contract, fresh_version, complete_study, outcome_type
):
    changed = copy.deepcopy(complete_study)
    changed["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]["type"] = (
        outcome_type
    )
    result = extract(contract, fresh_version, changed)
    assert len(result["reported_outcomes"]) == 1
    assert result["reported_outcomes"][0]["type"] == "PRIMARY"


@pytest.mark.parametrize(
    "malformed_class",
    [
        "not-an-object",
        {"categories": "not-a-list"},
        {"categories": ["not-an-object"]},
        {"categories": [{"measurements": "not-a-list"}]},
        {"categories": [{"measurements": ["not-an-object"]}]},
    ],
)
def test_valid_measurement_followed_by_malformed_structure_is_unsafe(
    contract, fresh_version, complete_study, malformed_class
):
    changed = copy.deepcopy(complete_study)
    changed["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0][
        "classes"
    ] = [
        {"categories": [{"measurements": [{"value": "-8.2"}]}]},
        malformed_class,
    ]
    result = extract(contract, fresh_version, changed)
    assert result["safe"] is False
    assert result["failure_code"] == "SOURCE_OUTCOME_MALFORMED"


def test_primary_empty_title_with_malformed_structure_is_unsafe(
    contract, fresh_version, complete_study
):
    changed = copy.deepcopy(complete_study)
    changed["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0][
        "title"
    ] = ""
    changed["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0][
        "classes"
    ] = [{"categories": "not-a-list"}]
    result = extract(contract, fresh_version, changed)
    assert result["safe"] is False
    assert result["failure_code"] == "SOURCE_OUTCOME_MALFORMED"


def test_secondary_malformed_structure_is_out_of_scope(
    contract, fresh_version, complete_study
):
    changed = copy.deepcopy(complete_study)
    changed["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]["type"] = (
        "SECONDARY"
    )
    changed["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0][
        "classes"
    ] = "not-a-list"
    result = extract(contract, fresh_version, changed)
    assert result["safe"] is True
    assert len(result["reported_outcomes"]) == 1
    assert result["reported_outcomes"][0]["type"] == "PRIMARY"


def test_primary_outcome_with_one_valid_nested_measurement_is_eligible(
    contract, fresh_version, complete_study
):
    changed = copy.deepcopy(complete_study)
    changed["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0][
        "classes"
    ] = [{"categories": [{"measurements": [{"value": " "}, {"value": "-8.2"}]}]}]
    result = extract(contract, fresh_version, changed)
    assert len(result["reported_outcomes"]) == 2
    assert result["reported_outcomes"][0]["has_data"] is True


@pytest.mark.parametrize(
    "classes",
    [
        "not-a-list",
        ["not-an-object"],
        [{"categories": "not-a-list"}],
        [{"categories": ["not-an-object"]}],
        [{"categories": [{"measurements": "not-a-list"}]}],
        [{"categories": [{"measurements": ["not-an-object"]}]}],
    ],
)
def test_malformed_nested_measurement_structure_is_unsafe(
    contract, fresh_version, complete_study, classes
):
    changed = copy.deepcopy(complete_study)
    changed["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0][
        "classes"
    ] = classes
    result = extract(contract, fresh_version, changed)
    assert result["safe"] is False
    assert result["failure_code"] == "SOURCE_OUTCOME_MALFORMED"


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


def test_missing_has_results_requests_more_info(
    contract, fresh_version, complete_study
):
    changed = copy.deepcopy(complete_study)
    del changed["hasResults"]
    result = extract(contract, fresh_version, changed)
    assert result["safe"] is True
    assert result["preliminary"] == "REQUEST_MORE_INFO"
    assert result["failure_code"] == "RESULTS_STATUS_MISSING"


@pytest.mark.parametrize("has_results", [None, "true", 1])
def test_non_boolean_has_results_requests_more_info(
    contract, fresh_version, complete_study, has_results
):
    changed = copy.deepcopy(complete_study)
    changed["hasResults"] = has_results
    result = extract(contract, fresh_version, changed)
    assert result["preliminary"] == "REQUEST_MORE_INFO"
    assert result["failure_code"] == "RESULTS_STATUS_MISSING"


def test_coherent_no_results_is_action_required(
    contract, fresh_version, complete_study
):
    changed = without_reported_results(complete_study)
    changed["hasResults"] = False
    changed["protocolSection"]["statusModule"].pop("resultsFirstPostDateStruct")
    result = extract(contract, fresh_version, changed)
    assert result["safe"] is True
    assert result["preliminary"] == "ACTION_REQUIRED"
    assert result["failure_code"] == "RESULTS_NOT_POSTED"
    assert len(result["registered_primary_outcomes"]) == 2


def test_malformed_registered_primary_data_is_unsafe_before_no_results_routing(
    contract, fresh_version, complete_study
):
    changed = without_reported_results(complete_study)
    changed["hasResults"] = False
    changed["protocolSection"]["statusModule"].pop("resultsFirstPostDateStruct")
    changed["protocolSection"]["outcomesModule"]["primaryOutcomes"] = "malformed"
    result = extract(contract, fresh_version, changed)
    assert result["safe"] is False
    assert result["verdict"] == "UNRESOLVED"
    assert result["failure_code"] == "SOURCE_OUTCOME_MALFORMED"


@pytest.mark.parametrize(
    ("has_results", "keep_posted_date", "keep_measurements"),
    [
        (False, True, False),
        (False, False, True),
        (False, True, True),
        (True, False, True),
        (True, False, False),
        (True, True, False),
    ],
)
def test_contradictory_results_evidence_is_unsafe(
    contract,
    fresh_version,
    complete_study,
    has_results,
    keep_posted_date,
    keep_measurements,
):
    changed = copy.deepcopy(complete_study)
    changed["hasResults"] = has_results
    if not keep_posted_date:
        changed["protocolSection"]["statusModule"].pop("resultsFirstPostDateStruct")
    if not keep_measurements:
        changed = without_reported_results(changed)
    result = extract(contract, fresh_version, changed)
    assert result["safe"] is False
    assert result["verdict"] == "UNRESOLVED"
    assert result["failure_code"] == "SOURCE_RESULTS_CONTRADICTORY"


@pytest.mark.parametrize(
    ("has_results", "keep_posted_date", "keep_measurements", "expected"),
    [
        (False, False, False, (True, "ACTION_REQUIRED", "RESULTS_NOT_POSTED")),
        (False, True, False, (False, "UNRESOLVED", "SOURCE_RESULTS_CONTRADICTORY")),
        (None, True, True, (True, "REQUEST_MORE_INFO", "RESULTS_STATUS_MISSING")),
        ("false", True, True, (True, "REQUEST_MORE_INFO", "RESULTS_STATUS_MISSING")),
    ],
)
def test_results_status_precedes_missing_decision_fields(
    contract,
    fresh_version,
    complete_study,
    has_results,
    keep_posted_date,
    keep_measurements,
    expected,
):
    changed = copy.deepcopy(complete_study)
    changed["hasResults"] = has_results
    changed["protocolSection"].pop("sponsorCollaboratorsModule")
    changed["protocolSection"]["outcomesModule"].pop("primaryOutcomes")
    if not keep_posted_date:
        changed["protocolSection"]["statusModule"].pop("resultsFirstPostDateStruct")
    if not keep_measurements:
        changed = without_reported_results(changed)
    result = extract(contract, fresh_version, changed)
    assert result["safe"] is expected[0]
    assert result["preliminary" if result["safe"] else "verdict"] == expected[1]
    assert result["failure_code"] == expected[2]


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
