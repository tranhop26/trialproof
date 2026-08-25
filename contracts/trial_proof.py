# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
import genlayer as gl
from genlayer import *
from datetime import datetime
import hashlib
import json
import unicodedata

VERSION = "trialproof/1.0.0"
POLICY_VERSION = "trialproof-disclosure/1"
WORKFLOW_VERSION = "trialproof-workflow/1"
ASSESSMENT_WINDOW_SECONDS = 604_800
MAX_PAGE_SIZE = 100
MAX_WEB_BODY_BYTES = 24_576
MAX_SOURCE_AGE_SECONDS = 432_000
MAX_SOURCE_FUTURE_SKEW_SECONDS = 300
MAX_OUTCOMES = 32
MAX_TEXT_LENGTH = 1_024
VERSION_URL = "https://clinicaltrials.gov/api/v2/version"
STUDY_FIELDS = "NCTId,LeadSponsorName,OverallStatus,PrimaryCompletionDate,ResultsFirstPostDate,PrimaryOutcomeMeasure,PrimaryOutcomeDescription,PrimaryOutcomeTimeFrame,HasResults,OutcomeType,OutcomeMeasureTitle,OutcomeMeasureDescription,OutcomeMeasurementValue"


class TrialProof(gl.Contract):
    next_assessment_id: u64
    assessments: TreeMap[str, str]
    assessment_ids: DynArray[str]
    nct_index: TreeMap[str, str]

    def __init__(self) -> None:
        self.next_assessment_id = u64(1)

    @gl.public.write
    def register_study(self, nct_id: str) -> str:
        canonical_nct_id = self._canonical_nct_id(nct_id)
        self._require(canonical_nct_id not in self.nct_index, "ASSESSMENT_ALREADY_EXISTS")
        now = self._transaction_timestamp()
        assessment_id = str(int(self.next_assessment_id))
        assessment = {
            "assessment_deadline": now + ASSESSMENT_WINDOW_SECONDS,
            "assessment_id": assessment_id,
            "attempt": 0,
            "certified": False,
            "created_at": now,
            "evidence_hash": "",
            "last_action": "REGISTER_STUDY",
            "nct_id": canonical_nct_id,
            "policy_version": POLICY_VERSION,
            "registrant": str(gl.message.sender_address).lower(),
            "resolution": {},
            "revision": 0,
            "state": "REGISTERED",
            "updated_at": now,
            "workflow_version": WORKFLOW_VERSION,
        }
        self._save_assessment(assessment_id, assessment)
        self.nct_index[canonical_nct_id] = assessment_id
        self.assessment_ids.append(assessment_id)
        self.next_assessment_id = u64(int(self.next_assessment_id) + 1)
        return self._receipt(assessment_id, "REGISTER_STUDY", "REGISTERED")

    @gl.public.view
    def get_assessment(self, assessment_id: str) -> str:
        return self._canonical_json(self._load_assessment(assessment_id))

    @gl.public.view
    def get_assessment_by_nct_id(self, nct_id: str) -> str:
        canonical_nct_id = self._canonical_nct_id(nct_id)
        if canonical_nct_id not in self.nct_index:
            return "{}"
        return self.get_assessment(self.nct_index[canonical_nct_id])

    @gl.public.view
    def get_assessment_count(self) -> int:
        return len(self.assessment_ids)

    @gl.public.view
    def get_assessment_ids_page(self, start: int, limit: int) -> list[str]:
        self._require(
            isinstance(start, int)
            and not isinstance(start, bool)
            and start >= 0
            and isinstance(limit, int)
            and not isinstance(limit, bool)
            and 1 <= limit <= MAX_PAGE_SIZE,
            "INVALID_PAGE",
        )
        stop = min(start + limit, len(self.assessment_ids))
        return [self.assessment_ids[index] for index in range(start, stop)]

    @gl.public.view
    def get_version(self) -> str:
        return VERSION

    def _canonical_nct_id(self, value: str) -> str:
        self._require(
            isinstance(value, str)
            and len(value) == 11
            and value[:3].lower() == "nct"
            and value[3:].isdigit()
            and value.isascii(),
            "INVALID_NCT_ID",
        )
        return "NCT" + value[3:]

    def _version_url(self) -> str:
        return VERSION_URL

    def _study_url(self, nct_id: str) -> str:
        canonical_nct_id = self._canonical_nct_id(nct_id)
        return (
            "https://clinicaltrials.gov/api/v2/studies/"
            + canonical_nct_id
            + "?format=json&fields="
            + STUDY_FIELDS
        )

    def _fetch_json(self, url: str) -> dict:
        try:
            response = gl.nondet.web.get(url)
            if isinstance(response, dict):
                status = response.get("status", response.get("status_code", 0))
                raw_body = response.get("body", response.get("text"))
            else:
                status = getattr(response, "status", getattr(response, "status_code", 0))
                raw_body = getattr(response, "body", None)
            if status != 200:
                return {"safe": False, "failure_code": "SOURCE_HTTP_ERROR"}
            if isinstance(raw_body, str):
                body = raw_body.encode("utf-8")
            elif isinstance(raw_body, bytes):
                body = raw_body
            else:
                return {"safe": False, "failure_code": "SOURCE_MALFORMED"}
            if len(body) == 0 or len(body) > MAX_WEB_BODY_BYTES:
                return {"safe": False, "failure_code": "SOURCE_TOO_LARGE"}
            value = json.loads(body.decode("utf-8"))
            if not isinstance(value, dict):
                return {"safe": False, "failure_code": "SOURCE_MALFORMED"}
            return {"safe": True, "data": value}
        except Exception:
            return {"safe": False, "failure_code": "SOURCE_MALFORMED"}

    def _unsafe_snapshot(self, code: str, observed_at: int) -> dict:
        return {
            "failure_code": code,
            "observed_at": observed_at,
            "safe": False,
            "verdict": "UNRESOLVED",
        }

    def _extract_source_snapshot(
        self, version_data: dict, study_data: dict, expected_nct_id: str, observed_at: int
    ) -> dict:
        if not isinstance(version_data, dict) or not isinstance(study_data, dict):
            return self._unsafe_snapshot("SOURCE_MALFORMED", observed_at)
        api_version = version_data.get("version")
        timestamp_text = version_data.get("dataTimestamp")
        if not isinstance(api_version, str) or not isinstance(timestamp_text, str):
            return self._unsafe_snapshot("SOURCE_VERSION_MALFORMED", observed_at)
        try:
            api_timestamp = int(
                datetime.fromisoformat(timestamp_text.replace("Z", "+00:00")).timestamp()
            )
        except Exception:
            return self._unsafe_snapshot("SOURCE_VERSION_MALFORMED", observed_at)
        if api_timestamp > observed_at + MAX_SOURCE_FUTURE_SKEW_SECONDS:
            return self._unsafe_snapshot("SOURCE_FUTURE", observed_at)
        if observed_at - api_timestamp > MAX_SOURCE_AGE_SECONDS:
            return self._unsafe_snapshot("SOURCE_STALE", observed_at)
        try:
            protocol = study_data["protocolSection"]
            identification = protocol["identificationModule"]
            source_nct_id = identification["nctId"]
        except Exception:
            return self._unsafe_snapshot("SOURCE_IDENTITY_MISSING", observed_at)
        if source_nct_id != expected_nct_id:
            return self._unsafe_snapshot("SOURCE_IDENTITY_MISMATCH", observed_at)
        sponsor = identification.get("organization", {}).get("fullName", "")
        sponsor_identity = self._safe_text(sponsor).casefold() if self._safe_text(sponsor) else ""
        status_module = protocol.get("statusModule", {})
        completion = status_module.get("primaryCompletionDateStruct", {}).get("date", "")
        results_posted = status_module.get("resultsFirstPostDateStruct", {}).get("date", "")
        overall_status = status_module.get("overallStatus", "")
        primary_outcomes = protocol.get("outcomesModule", {}).get("primaryOutcomes")
        reported_outcomes = (
            study_data.get("resultsSection", {})
            .get("outcomeMeasuresModule", {})
            .get("outcomeMeasures", [])
        )
        snapshot = {
            "api_data_timestamp": api_timestamp,
            "api_version": api_version,
            "failure_code": "",
            "has_results": study_data.get("hasResults") is True,
            "nct_id": source_nct_id,
            "observed_at": observed_at,
            "overall_status": self._safe_text(overall_status) or "",
            "primary_completion_date": self._safe_text(completion) or "",
            "registered_primary_outcomes": [],
            "reported_outcomes": [],
            "results_first_post_date": self._safe_text(results_posted) or "",
            "safe": True,
            "source_host": "clinicaltrials.gov",
            "sponsor_identity": sponsor_identity,
        }
        if not sponsor_identity:
            snapshot["preliminary"] = "REQUEST_MORE_INFO"
            snapshot["failure_code"] = "SPONSOR_MISSING"
            return snapshot
        if not isinstance(primary_outcomes, list) or len(primary_outcomes) == 0:
            snapshot["preliminary"] = "REQUEST_MORE_INFO"
            snapshot["failure_code"] = "PRIMARY_OUTCOMES_MISSING"
            return snapshot
        if len(primary_outcomes) > MAX_OUTCOMES or not isinstance(reported_outcomes, list) or len(reported_outcomes) > MAX_OUTCOMES:
            return self._unsafe_snapshot("SOURCE_OUTCOMES_UNBOUNDED", observed_at)
        for outcome in primary_outcomes:
            if not isinstance(outcome, dict):
                return self._unsafe_snapshot("SOURCE_OUTCOME_MALFORMED", observed_at)
            measure = self._safe_text(outcome.get("measure"))
            if not measure:
                snapshot["preliminary"] = "REQUEST_MORE_INFO"
                snapshot["failure_code"] = "PRIMARY_OUTCOMES_MISSING"
                return snapshot
            snapshot["registered_primary_outcomes"].append(
                {
                    "description": self._safe_text(outcome.get("description")) or "",
                    "measure": measure,
                    "time_frame": self._safe_text(outcome.get("timeFrame")) or "",
                }
            )
        for outcome in reported_outcomes:
            if not isinstance(outcome, dict):
                return self._unsafe_snapshot("SOURCE_OUTCOME_MALFORMED", observed_at)
            title = self._safe_text(outcome.get("title"))
            if not title:
                continue
            snapshot["reported_outcomes"].append(
                {
                    "description": self._safe_text(outcome.get("description")) or "",
                    "has_data": bool(outcome.get("classes")),
                    "title": title,
                    "type": self._safe_text(outcome.get("type")) or "",
                }
            )
        if not snapshot["primary_completion_date"]:
            snapshot["preliminary"] = "REQUEST_MORE_INFO"
            snapshot["failure_code"] = "COMPLETION_DATE_MISSING"
            return snapshot
        snapshot["preliminary"] = "READY_FOR_SEMANTIC_REVIEW"
        return snapshot

    def _safe_text(self, value) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = unicodedata.normalize("NFKC", value)
        if any(unicodedata.category(character) == "Cc" for character in normalized):
            return None
        text = " ".join(normalized.split())
        return text if 0 < len(text) <= MAX_TEXT_LENGTH else None

    def _hash_snapshot(self, snapshot: dict) -> str:
        payload = self._canonical_json(snapshot).encode("utf-8")
        return "0x" + hashlib.sha256(payload).hexdigest()

    def _action_domain(
        self,
        assessment_id: str,
        assessment: dict,
        evidence_hash: str,
        action: str,
        revision: int,
        attempt: int,
    ) -> str:
        payload = self._canonical_json(
            {
                "action": action,
                "assessment_id": assessment_id,
                "attempt": attempt,
                "chain_id": str(gl.message.chain_id),
                "contract": str(gl.message.contract_address).lower(),
                "evidence_hash": evidence_hash,
                "nct_id": assessment["nct_id"],
                "policy_version": POLICY_VERSION,
                "revision": revision,
            }
        )
        return "0x" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _load_assessment(self, assessment_id: str) -> dict:
        self._require(
            isinstance(assessment_id, str) and assessment_id in self.assessments,
            "ASSESSMENT_NOT_FOUND",
        )
        return json.loads(self.assessments[assessment_id])

    def _save_assessment(self, assessment_id: str, assessment: dict) -> None:
        self.assessments[assessment_id] = self._canonical_json(assessment)

    def _receipt(self, assessment_id: str, action: str, state: str) -> str:
        return self._canonical_json(
            {"action": action, "assessment_id": assessment_id, "state": state}
        )

    def _transaction_timestamp(self) -> int:
        transaction_datetime = gl.message_raw["datetime"]
        return int(
            datetime.fromisoformat(transaction_datetime.replace("Z", "+00:00")).timestamp()
        )

    def _canonical_json(self, value) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def _require(self, condition: bool, code: str) -> None:
        if not condition:
            raise Exception(code)
