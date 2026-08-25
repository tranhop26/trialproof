# Verification results

Status: offline and live Studionet verification passed on 2026-08-25.

- Source commit: `394c3b24bce8476638d6c98d7563710bbc7ae6f6`
- Deployment artifact SHA-256: `99ebd24c898cf2dccec264324c1a0e5066d1ca3e5f5de468107d3a48a08a4072`
- Deployment artifact size: `19,505` bytes
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
| Contract deployment | PASS | Studionet tx `0xac22c762...1e18672b`; `FINALIZED`; GenVM `SUCCESS` |
| Live integration | PASS | Happy-path register/assess txs `0xa47427ed...f54d913b` / `0xb3c07509...12214aa5` and safe-branch txs `0x0e1ded7c...27d20934` / `0xa25b2654...1adc7b4b`; all `FINALIZED` / `SUCCESS` |
| Sample transaction/readback | PASS | Happy-path ID and NCT reads match with `DISCLOSURE_COMPLETE`; unavailable-source reads also match with `UNRESOLVED`, not certified, `SOURCE_HTTP_ERROR` |

The earlier immutable `trialproof/1.0.0` instance safely returned `REQUEST_MORE_INFO` after exposing a sponsor-path compatibility issue. It was not upgraded. Version `1.0.1` was regression-tested and deployed as a separate frozen successor.
