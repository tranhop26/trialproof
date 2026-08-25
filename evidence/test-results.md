# Verification results

Status: offline verification passed on 2026-08-25; live deployment not performed.

- Source commit: `6b61d5215696656cd1681d64cd0b35d08ebce08e`
- Deployment artifact SHA-256: `3776e4b52191ffc0a71656fa9ef272572f39755b8ab4f19ff9aa5576adebccb3`
- Deployment artifact size: `19,320` bytes
- Dependency hash: `1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`

| Check | Result | Evidence |
|---|---|---|
| Formatter | PASS | 11 files already formatted |
| GenVM linter | PASS | 3 checks; schema validation passed; 10 public methods |
| Direct + artifact/tooling tests | PASS | 41 passed |
| RPC integration preflight | PARTIAL | 2 passed; finalized lifecycle skipped because `http://127.0.0.1:4000/api` was unavailable |
| TypeScript tests | PASS | 4 files, 30 tests passed |
| TypeScript typecheck | PASS | `tsc --noEmit` exited 0 |
| Contract deployment | NOT_DEPLOYED | requires action-time wallet confirmation |
| Sample transaction/readback | NOT_EXECUTED | requires verified deployment |

No live address, transaction hash, explorer link, or readback is claimed before verification.
