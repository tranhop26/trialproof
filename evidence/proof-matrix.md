# Proof matrix

Offline source commit: `65237869a948a1431b5cbf3e3259cff0d7bc442e`. Exact artifact SHA-256: `522241d618a791470803f07ff8b3008628fd6e2f3caffc9970f645f8ffd7020d`.

| Actor | Action | Contract method | Transaction hash | Finalized / execution | Readback | Source/test |
|---|---|---|---|---|---|---|
| Unrelated direct-test address | Assess complete record | `assess` | direct test; no live hash | direct VM success | `DISCLOSURE_COMPLETE`, certified | `tests/direct/test_consensus.py` |
| Unrelated direct-test address | Expire unresolved case | `expire_assessment` | direct test; no live hash | direct VM success | `UNRESOLVED`, not certified | `tests/direct/test_liveness.py` |
| Live deployer | Deploy exact artifact | deployment | NOT_DEPLOYED | NOT_VERIFIED | NOT_VERIFIED | action-time confirmation required |
| Live sample caller | Register and assess `NCT04516746` | `register_study`, `assess` | NOT_EXECUTED | NOT_VERIFIED | NOT_VERIFIED | source preflight passed; verified deployment required |

This matrix intentionally distinguishes direct-test proof from live-chain evidence.
