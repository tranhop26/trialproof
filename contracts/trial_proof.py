# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
import genlayer as gl
from genlayer import *
from datetime import datetime
import json

VERSION = "trialproof/1.0.0"
POLICY_VERSION = "trialproof-disclosure/1"
WORKFLOW_VERSION = "trialproof-workflow/1"
ASSESSMENT_WINDOW_SECONDS = 604_800
MAX_PAGE_SIZE = 100


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
