# Verification results

Status: offline verification passed on 2026-08-25; live deployment not performed.

- Source commit: `65237869a948a1431b5cbf3e3259cff0d7bc442e`
- Deployment artifact SHA-256: `522241d618a791470803f07ff8b3008628fd6e2f3caffc9970f645f8ffd7020d`
- Deployment artifact size: `19,479` bytes
- Dependency hash: `1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`

| Check | Result | Evidence |
|---|---|---|
| Formatter | PASS | 11 files already formatted |
| GenVM linter | PASS | 3 checks; schema validation passed; 10 public methods |
| Direct + artifact/tooling tests | PASS | 41 passed |
| RPC integration preflight | PARTIAL | 2 passed; finalized lifecycle skipped because `http://127.0.0.1:4000/api` was unavailable |
| TypeScript tests | PASS | 4 files, 30 tests passed |
| TypeScript typecheck | PASS | `tsc --noEmit` exited 0 |
| Official-source compatibility | PASS | ClinicalTrials.gov API `2.0.5`; `NCT04516746` returned 4 registered and 4 reported primary outcomes in 19,497 bytes |
| Contract deployment | NOT_DEPLOYED | requires action-time wallet confirmation |
| Sample transaction/readback | NOT_EXECUTED | requires verified deployment |

No live address, transaction hash, explorer link, or readback is claimed before verification.
