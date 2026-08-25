# Proof matrix

| Actor | Action | Contract method | Transaction hash | Finalized / execution | Readback | Source/test |
|---|---|---|---|---|---|---|
| Unrelated direct-test address | Assess complete record | `assess` | direct test; no live hash | direct VM success | `DISCLOSURE_COMPLETE`, certified | `tests/direct/test_consensus.py` |
| Unrelated direct-test address | Expire unresolved case | `expire_assessment` | direct test; no live hash | direct VM success | `UNRESOLVED`, not certified | `tests/direct/test_liveness.py` |
| Live deployer | Deploy exact artifact | deployment | NOT_DEPLOYED | NOT_VERIFIED | NOT_VERIFIED | action-time confirmation required |
| Live sample caller | Register and assess public NCT record | `register_study`, `assess` | NOT_EXECUTED | NOT_VERIFIED | NOT_VERIFIED | verified deployment required |

This matrix intentionally distinguishes direct-test proof from live-chain evidence.
