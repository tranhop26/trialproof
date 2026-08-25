# Verification results

Status: offline verification pending final rerun; live deployment not performed.

| Check | Result | Evidence |
|---|---|---|
| Formatter | PENDING | `ruff format --check contracts tests scripts` |
| GenVM linter | PENDING | UTF-8 `genvm-lint check contracts/trial_proof.py` |
| Direct tests | PENDING | `pytest tests/direct -v` |
| Artifact/tooling tests | PENDING | `pytest tests/tooling -v` |
| RPC integration | PENDING | local RPC currently unavailable; skip is not success |
| TypeScript tests | PENDING | `npm test` |
| TypeScript typecheck | PENDING | `npm run typecheck` |
| Contract deployment | NOT_DEPLOYED | requires action-time wallet confirmation |
| Sample transaction/readback | NOT_EXECUTED | requires verified deployment |

No live address, transaction hash, explorer link, or readback is claimed before verification.
