# Verification results

Status: local verification recorded on 2026-09-01 for the fixed
`trialproof/1.1.0` candidate. This is not live deployment evidence. The
historical `trialproof/1.0.1` Studionet deployment remains bound to
`deployments/studionet.json` and has not been relabeled or modified.

- Local candidate source commit: `e6db12e91a59d0c1e0215ff1da57a9d26ab3cc6e` (`fix: validate primary outcome result evidence`). This identifies local candidate source only; it is not a deployed-contract commit.
- Readable source SHA-256 (`contracts/trial_proof.py`): `3BBE5E461E349B1CA6CB6C30537E98DE5DEC94071EDCDCED60FE866CA9158A10`
- Deployment artifact SHA-256 (`deploy/source/trial_proof.py`): `8B1EAC2585F6C280506C3609C80103612FB75CD4E8BEF0E00234BBA2851DB13C`
- Deployment artifact size: `21,728` bytes

| Command | Result | Observed output |
|---|---|---|
| `ruff format --check contracts tests scripts` | PASS | 11 files already formatted |
| `$env:PYTHONIOENCODING = "utf-8"; genvm-lint check contracts/trial_proof.py` | PASS | 3 checks; validation passed; 10 methods (5 view, 5 write) |
| `python scripts/build_bradbury_contract.py --check` | PASS | exited 0 |
| `pytest tests/direct tests/tooling -v` | PASS | 86 passed |
| `pytest tests/integration -v` | PASS with documented skip | 2 passed, 1 skipped (`TRIALPROOF_RPC_UNAVAILABLE`) |
| `npm test` | PASS | 4 files passed; 38 tests passed |
| `npm run typecheck` | PASS | `tsc --noEmit` exited 0 |
| `git diff --check` | PASS | exited 0 |

The skipped RPC lifecycle test is not live-chain evidence. No `1.1.0` contract
address, deployment transaction, explorer source verification, finalized
execution, or contract readback is recorded here because none was observed.

The readable source and size-bounded deployment artifact have different hashes
by design. `python scripts/build_bradbury_contract.py --check` passing is the
local proof that the checked-in artifact deterministically derives from the
readable source; it does not establish correspondence to a deployed contract.
