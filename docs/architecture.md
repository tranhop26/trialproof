# Architecture and trust model

## Trust matrix

| Actor | Cannot trust | Can manipulate | Contract defense | Test evidence |
|---|---|---|---|---|
| Sponsor/investigator | reviewer or downstream consumer | narrative and request timing | only a canonical NCT ID is accepted; official URLs are constructed in contract | registry and evidence tests |
| Reviewer/funder/publisher | sponsor | claims of completeness | validators fetch the official record and match every primary outcome | consensus tests |
| Caller/relayer | both parties | call order, retry and replay | state guards, cooldown, attempt/revision counters and action-domain hashes | liveness tests |
| Validator | other validators and changing web | interpretation | independent fetch/evaluation and semantic decision-field comparison | equivalence tests |
| Deployer | users | policy replacement or verdict override | frozen ABI without privileged methods | recoverability/schema tests |

## Data flow

1. Any address registers a canonical NCT ID. Duplicate registration for the policy version is rejected.
2. Any address calls `assess` before the original assessment deadline.
3. Leader and validators independently fetch the fixed API version and study endpoints.
4. Deterministic guards reject transport, size, freshness, identity and structural failures; they parse registered primary outcomes before negative-status routing so deterministic no-results resolutions retain truthful count and missing-index metadata, then filter reported results to eligible `PRIMARY` outcomes with validated non-empty nested measurement values.
5. Contradictory `hasResults`, results-posted-date, or eligible-primary-data evidence is stored as `UNRESOLVED` before any semantic interpretation. Coherent negative status is deterministic `ACTION_REQUIRED` even when unrelated sponsor or completion fields are missing; otherwise the LLM maps registered primary outcomes only to the filtered eligible results.
6. The comparative validator checks decision-bearing semantic fields, not raw JSON or rationale wording.
7. The contract stores the verdict, evidence hash, source timestamp, attempt, revision and action domain.
8. Clients wait for finality and execution success, then read contract state.

## State machine

| From | Actor | Method | Preconditions | To |
|---|---|---|---|---|
| none | any | `register_study` | canonical unique NCT ID | `REGISTERED` |
| `REGISTERED` | any | `assess` | before deadline | validator verdict |
| `REGISTERED` | any | `expire_assessment` | deadline reached | `UNRESOLVED` |
| `ACTION_REQUIRED`, `REQUEST_MORE_INFO`, `UNRESOLVED` | any | `refresh` | cooldown reached; attempts below 3 | validator verdict |
| retryable state | any | `close_after_max_attempts` | attempts equal 3 | `CLOSED_UNCERTIFIED` |
| `DISCLOSURE_COMPLETE`, `CLOSED_UNCERTIFIED` | none | none | terminal | unchanged |

`DISCLOSURE_COMPLETE` is the only certified state. Every other state has `certified=false`.

## Evidence failures

Unavailable, non-200, oversized, malformed, stale, future-skewed, wrong-NCT, malformed registered-primary structures, structurally invalid nested result data, or contradictory status/date/eligible-primary-data evidence cannot certify and is routed to `UNRESOLVED` before semantic interpretation. Missing but accessible record fields become `REQUEST_MORE_INFO`; coherent no-results still records `ACTION_REQUIRED` when the registered-primary field is merely absent or empty, because status precedence prevents a favorable default. A nondeterministic transaction that cannot reach consensus does not advance state; after the fixed deadline, an unrelated address can safely record `UNRESOLVED` through `expire_assessment`.

## Recoverability

TrialProof is `INTENTIONALLY_FROZEN`. Migration means deploying a separately reviewed version, registering a new assessment there, and preserving the old address for audit. There is no privileged in-place repair.
