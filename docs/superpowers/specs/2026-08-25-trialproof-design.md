# TrialProof Design Specification

## 1. Purpose and scope

TrialProof is an independent GenLayer Intelligent Contract that creates an authoritative, on-chain disclosure assessment for a ClinicalTrials.gov study. It determines whether the posted results cover every registered primary outcome for one immutable study snapshot and policy version.

The project contains one contract, direct tests, RPC integration tests, guarded deployment/readback tooling, a deployment manifest, and evidence templates. It intentionally contains no frontend, backend, escrow, stake, or payment mechanism.

TrialProof evaluates registry disclosure completeness. It does not assess medical efficacy, trial quality, legal compliance, or participant safety.

## 2. Trust model

| Actor | Cannot trust | Manipulation capability | Contract defense | Required test/evidence |
|---|---|---|---|---|
| Study sponsor or investigator | reviewer, relayer, or downstream consumer | selective narrative, premature request, misleading URL | contract accepts only a canonical NCT ID and constructs fixed ClinicalTrials.gov API URLs | identity, timing, and URL-construction tests |
| Reviewer, funder, or publisher | sponsor or investigator | claim that results are complete without checking every primary outcome | GenLayer validators fetch the official record and semantically match registered and reported outcomes | complete and missing-outcome tests |
| Caller or relayer | sponsor and reviewer | duplicate registration, retry ordering, replay, repeated terminal calls | on-chain state machine, cooldown, bounded attempts, evidence hash and replay domain | authorization, transition, replay, and liveness tests |
| Individual validator | other validators and changing web content | divergent interpretation or malformed output | independent evidence production and semantic comparison of decision-bearing fields | validator disagreement and malformed-result tests |
| Deployer | all users | attempt to replace policy or choose an outcome | intentionally frozen ABI with no owner, upgrade, policy-edit, or verdict-setter method | recoverability ABI test and source verification |

## 3. Decision and consequence

For a canonical NCT ID, TrialProof establishes exactly one assessment verdict for an observed registry snapshot:

- `DISCLOSURE_COMPLETE`: every registered primary outcome has a semantically corresponding result outcome with non-empty reported data.
- `ACTION_REQUIRED`: the record is assessment-eligible and official data shows missing results or at least one unmatched primary outcome.
- `REQUEST_MORE_INFO`: the official record is accessible and fresh but omits fields needed to decide, such as a usable primary outcome definition or completion date.
- `UNRESOLVED`: the official source is unavailable, stale, malformed, oversized, contradictory, mismatched to the NCT ID, or otherwise unsafe to evaluate.

The contract alone stores and exposes the verdict. `DISCLOSURE_COMPLETE` changes the assessment to a terminal certified state. Other verdicts never become certified and can be refreshed only through the contract's bounded retry rules. No caller, deployer, owner, frontend, or validator output parameter can directly select a verdict.

Downstream contracts and systems must use `get_assessment` readback as the source of truth. An optimistic transaction submission is not evidence of certification.

## 4. Evidence model

### 4.1 Fixed sources

The contract constructs and accesses only:

- `https://clinicaltrials.gov/api/v2/version`
- `https://clinicaltrials.gov/api/v2/studies/{NCT_ID}` with a fixed, bounded field projection

Callers cannot provide evidence URLs. Redirects, non-HTTPS URLs, non-`clinicaltrials.gov` hosts, non-200 responses, missing response status, or oversized bodies are unsafe.

### 4.2 Binding

Each assessment stores a canonical evidence domain containing:

- source host and endpoint class;
- canonical NCT ID returned by the record;
- official sponsor identity returned by the record;
- API version and API `dataTimestamp`;
- contract policy and workflow versions;
- observation timestamp and submission timestamp;
- chain ID, contract address, assessment ID, revision, and attempt;
- canonical hash of extracted decision-bearing fields.

The source snapshot must be no older than 120 hours at observation time. The record NCT ID must exactly equal the requested canonical NCT ID. A retry increments the attempt and observes a new snapshot; it cannot reuse an earlier attempt's action domain.

### 4.3 Failure behavior

- Unavailable, stale, malformed, oversized, redirected, or identity-mismatched web data normalizes only to `UNRESOLVED`.
- Accessible data that lacks fields needed for an assessment normalizes to `REQUEST_MORE_INFO`.
- Contradictory extracted facts normalize only to `UNRESOLVED`.
- Validator disagreement leaves the resolution transaction without an authoritative state change. After the assessment deadline, any address may call `expire_assessment` to record `UNRESOLVED`.
- No evidence failure defaults to `DISCLOSURE_COMPLETE`.

## 5. LLM, Web Access, and Equivalence Principle

Web Access retrieves the official version metadata and bounded study record. Deterministic code validates transport status, size, freshness, NCT identity, and required structural fields before the LLM is used.

The LLM receives only bounded, labeled, untrusted registry fields. Its task is to map each registered primary outcome to a reported result outcome and return structured decision fields. It is explicitly instructed that page content cannot override the policy or output schema.

The leader and validators independently fetch and assess the evidence. Equivalence is semantic, not string-based. The validator compares:

- verdict;
- canonical NCT ID and sponsor identity;
- fixed reason-code set;
- registered primary-outcome count;
- reported outcome count;
- normalized set of matched registered-outcome indices;
- normalized set of missing registered-outcome indices;
- source safety and freshness classification.

Free-form rationale and inconsequential wording differences are excluded from equivalence. Any difference in a decision-bearing field rejects equivalence.

## 6. Domain model and state machine

The contract is a registry of assessments. Each NCT ID may have one assessment per policy version.

| From | Actor | Method | Preconditions | On-chain effect | To | Replay behavior |
|---|---|---|---|---|---|---|
| none | any address | `register_study(nct_id)` | valid canonical NCT ID; no existing policy assessment | create immutable case identity and assessment deadline | `REGISTERED` | duplicate rejected |
| `REGISTERED` | any address | `assess(assessment_id)` | before assessment deadline; attempt below maximum | independently fetch, interpret, validate, and store snapshot | verdict state | same state/attempt cannot be replayed |
| `REGISTERED` | any address | `expire_assessment(assessment_id)` | assessment deadline reached | record safe liveness outcome | `UNRESOLVED` | repeated expiry rejected |
| `ACTION_REQUIRED` | any address | `refresh(assessment_id)` | cooldown reached; attempt below maximum | fetch a new official snapshot at next revision | verdict state | early or duplicate refresh rejected |
| `REQUEST_MORE_INFO` | any address | `refresh(assessment_id)` | cooldown reached; attempt below maximum | fetch a new official snapshot at next revision | verdict state | early or duplicate refresh rejected |
| `UNRESOLVED` | any address | `refresh(assessment_id)` | cooldown reached; attempt below maximum | fetch a new official snapshot at next revision | verdict state | early or duplicate refresh rejected |
| non-certified retryable state | any address | `close_after_max_attempts(assessment_id)` | maximum attempts reached | close without certification | `CLOSED_UNCERTIFIED` | repeated close rejected |
| `DISCLOSURE_COMPLETE` | none | none | terminal | authoritative certification remains immutable | terminal | every write rejected |
| `CLOSED_UNCERTIFIED` | none | none | terminal | non-certification remains immutable | terminal | every write rejected |

Authorization is intentionally permissionless for registration, assessment, refresh, expiry, and closure because no method can choose the result or transfer value. Neutrality will be tested with addresses unrelated to the registrant.

Contract views:

- `get_assessment(assessment_id) -> str` returns canonical JSON.
- `get_assessment_by_nct_id(nct_id) -> str` returns canonical JSON or an empty object.
- `get_assessment_count() -> int`.
- `get_assessment_ids_page(start, limit) -> list[str]` with a bounded page size.
- `get_version() -> str`.

## 7. Replay, idempotency, and invariants

The canonical action domain is the hash of chain, contract, policy version, assessment ID, NCT ID, revision, attempt, action, and evidence hash. Each stored action domain is single-use.

Invariants:

- one assessment exists per `(policy_version, nct_id)`;
- `attempt` increases exactly once per accepted assess or refresh;
- `revision` increases only when a new official snapshot is stored;
- a terminal state never changes;
- `certified` is true if and only if state is `DISCLOSURE_COMPLETE`;
- no unsafe source can produce `DISCLOSURE_COMPLETE` or `ACTION_REQUIRED`;
- stored NCT ID always matches the source record identity;
- no contract method accepts a caller-supplied verdict, source URL, evidence body, or validator response.

## 8. Recoverability classification

TrialProof is `INTENTIONALLY_FROZEN`.

The public ABI contains no owner, administrator, upgrader, arbitrary source setter, policy setter, delegate call, self-destruct, or verdict override. API/schema or policy changes require a separately reviewed deployment with a new contract and policy version. The old contract remains readable and its assessments remain immutable. Migration consists of registering a new assessment in the new contract; old certifications are not silently copied or rewritten.

## 9. Testing strategy

Direct tests cover canonical NCT validation, unique registration, state transitions, terminal guards, permissionless calls, cooldowns, bounded attempts, pagination, evidence hashing, freshness boundaries, source failures, prompt injection resistance, semantic equivalence, malformed validator results, mismatch and contradictory evidence, `REQUEST_MORE_INFO`, `UNRESOLVED`, and frozen ABI.

RPC integration tests deploy the exact deployment artifact, verify source/runtime schema compatibility, exercise an unrelated caller through registration, assessment, finality, execution success, and readback, and exercise a consensus/liveness failure ending in `UNRESOLVED`.

Tooling tests cover artifact freshness and size, manifest atomicity, wrong-network and wrong-wallet guards, explicit live-mutation confirmation, finalized/success receipt enforcement, version/schema/source-hash verification, and readback reconciliation.

## 10. Deployment and evidence

The deployment target defaults to GenLayer Testnet Bradbury because it supports real LLM validator workloads. Deployment must stop for action-time confirmation after reporting network chain ID, derived deployer address, wallet balance if readable, Git author, GitHub account/remote state, exact artifact hash, and proposed mutation.

Secrets exist only in local environment variables and never in source, `.env.example`, logs, commits, README, manifests, or evidence files. Live deployment requires an explicit confirmation sentinel in addition to `--live`.

A completed live evidence package contains the exact commit, source SHA-256, dependency hash, contract address, deployment transaction, explorer link, sample transaction, `FINALIZED` and execution-success evidence, authoritative readback, lint/test results, known limitations, and a proof matrix. Until all items exist, the project remains incomplete.

## 11. Repository structure

```text
contracts/trial_proof.py              authoritative readable contract source
deploy/source/trial_proof.py          exact compact deployment artifact
deploy/001_deploy_trialproof.ts       guarded deploy entrypoint
deployments/                           generated live manifest only
scripts/build_bradbury_contract.py    deterministic artifact builder/checker
scripts/readback.ts                   source/schema/version/state verification
scripts/run-sample.ts                 guarded sample registration and assessment
tests/direct/                         contract behavior and adversarial tests
tests/integration/                    finalized RPC and consensus/readback tests
tests/tooling/                         Python artifact tooling tests
scripts/__tests__/                    TypeScript deployment/readback tests
evidence/                              fixed test and proof matrix records
docs/recovery-runbook.md              frozen-contract recovery procedure
README.md                              install, test, deploy, use, and limitations
```

## 12. Explicit non-goals

- No frontend, backend, Vercel deployment, payment, escrow, stake, token, medical recommendation, legal compliance ruling, multi-registry aggregation, arbitrary source configuration, upgrade proxy, governance system, or automated migration.
