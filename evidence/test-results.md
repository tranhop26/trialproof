# Verification results

Status: repository, local verification, CI, and live deployment evidence recorded
on 2026-09-01 for `trialproof/1.1.0`.

- Verified source commit: `7ec17582e82893da85b6ff0349fac6e5b78325ec` (`docs: record finalized TrialProof 1.1.0 deployment`).
- Successful GitHub Actions run: [CI run 33458937195](https://github.com/tranhop26/trialproof/actions/runs/33458937195).
- Readable source SHA-256 (`contracts/trial_proof.py`): `3bbe5e461e349b1ca6cb6c30537e98de5dec94071edcdced60fe866ca9158a10`.
- Exact deployed artifact SHA-256 (`deploy/source/trial_proof.py`): `8b1eac2585f6c280506c3609c80103612fb75cd4e8bef0e00234bba2851db13c`.
- Exact deployed artifact size: `21,728` bytes.
- Studionet contract: [`0xa13693E7A524Bff515227e48256400d1cB67b221`](https://explorer-studio.genlayer.com/address/0xa13693E7A524Bff515227e48256400d1cB67b221).
- Finalized deployment transaction: [`0x8f8c0a74f51b2fa53df6341bba31991687c4c22f0cf979777d9d37e7ccc50233`](https://explorer-studio.genlayer.com/tx/0x8f8c0a74f51b2fa53df6341bba31991687c4c22f0cf979777d9d37e7ccc50233).
- Deployment identity: Studionet chain ID `61999`, deployer `0x21b45103dd05c43969daF3CbB4277391777e2eC7`.
- Live readback: version `trialproof/1.1.0`, initial assessment count `0`, and deployed source hash matched the checked-in artifact.
- Live 1.1.0 happy-path registration: [`0xf5396825e1a23787071a34ea5c3b896bd3e3d7d4d2a0051378577a248ff6af55`](https://explorer-studio.genlayer.com/tx/0xf5396825e1a23787071a34ea5c3b896bd3e3d7d4d2a0051378577a248ff6af55), `FINALIZED`, `MAJORITY_AGREE`, leader execution `SUCCESS`.
- Live 1.1.0 happy-path assessment: [`0xa52f883c39aad1edf2dd00c9fe18b6ecb4445c4637792b16e2b1b3eb1515f514`](https://explorer-studio.genlayer.com/tx/0xa52f883c39aad1edf2dd00c9fe18b6ecb4445c4637792b16e2b1b3eb1515f514), `FINALIZED`, `MAJORITY_AGREE`, leader execution `SUCCESS`.
- Live assessment readback: assessment `1`, NCT `NCT04516746`, state/verdict `DISCLOSURE_COMPLETE`, `certified=true`, 4 registered primary outcomes, 4 eligible reported `PRIMARY` outcomes, all four matched, none missing, source safe and fresh. Readback by assessment ID and NCT ID was identical.

| Command | Result | Observed output |
|---|---|---|
| `ruff format --check contracts tests scripts` | PASS | 11 files already formatted |
| `$env:PYTHONIOENCODING = "utf-8"; genvm-lint check contracts/trial_proof.py` | PASS | validation passed; 10 methods (5 view, 5 write) |
| `python scripts/build_bradbury_contract.py --check` | PASS | checked-in deployment artifact reproduced exactly |
| `pytest tests/direct tests/tooling -q` | PASS | 86 passed |
| `pytest tests/integration -q` | PASS with documented skip | 2 passed, 1 skipped (`TRIALPROOF_RPC_UNAVAILABLE`) |
| `npm test` | PASS | 4 files passed; 42 tests passed |
| `npm run typecheck` | PASS | `tsc --noEmit` exited 0 |
| `git diff --check` | PASS | exited 0 |

The regression suite now proves that certification considers only reported
outcomes whose type is exactly `PRIMARY`, requires at least one nested
measurement with a non-empty string value, rejects malformed measurement
structures, and resolves contradictions among `hasResults`, results-posted
date, and eligible result data to non-certifying `UNRESOLVED` state. Consensus
tests also compare decisive semantic fields rather than accepting output shape
alone.

The readable source and size-bounded deployment artifact have different hashes
by design. The reproducible-build check proves that the checked-in artifact is
deterministically derived from the readable source. The deployment manifest,
Explorer source, and live readback bind that exact artifact to the Studionet
address above.

Known limitation: the 1.1.0 happy path is now proven live, but no live 1.1.0
important non-certifying branch has been recorded yet. Contradictory results
status and malformed/insufficient primary measurements remain supported by
local and CI regression tests, not a live 1.1.0 assessment transaction.
Historical 1.0.1 assessment transactions remain audit evidence for the earlier
contract only.
