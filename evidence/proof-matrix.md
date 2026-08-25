# Proof matrix

Source commit: `394c3b24bce8476638d6c98d7563710bbc7ae6f6`. Exact artifact SHA-256: `99ebd24c898cf2dccec264324c1a0e5066d1ca3e5f5de468107d3a48a08a4072`.

| Actor | Action | Contract method | Transaction hash | Finalized / execution | Readback | Source/test |
|---|---|---|---|---|---|---|
| Unrelated direct-test address | Assess complete record | `assess` | direct test; no live hash | direct VM success | `DISCLOSURE_COMPLETE`, certified | `tests/direct/test_consensus.py` |
| Unrelated direct-test address | Expire unresolved case | `expire_assessment` | direct test; no live hash | direct VM success | `UNRESOLVED`, not certified | `tests/direct/test_liveness.py` |
| Live deployer `0x21b451...7e2eC7` | Deploy exact `1.0.1` artifact | deployment | `0xac22c762...1e18672b` | `FINALIZED` / `SUCCESS` | version `1.0.1`, count `0`; Explorer code inspected | Studionet Explorer |
| Live sample caller `0x21b451...7e2eC7` | Register `NCT04516746` | `register_study` | `0xa47427ed...f54d913b` | `FINALIZED` / `SUCCESS` | assessment `1`, `REGISTERED` | Studio finalized read |
| Live sample caller `0x21b451...7e2eC7` | Assess `NCT04516746` | `assess` | `0xb3c07509...12214aa5` | `FINALIZED` / `SUCCESS`, consensus accepted | `DISCLOSURE_COMPLETE`, certified, 4 matched / 0 missing | Studio finalized reads by ID and NCT ID |
| Live safe-branch caller `0x21b451...7e2eC7` | Register unavailable record `NCT99999999` | `register_study` | `0x0e1ded7c...27d20934` | `FINALIZED` / `SUCCESS`, consensus accepted | assessment `2`, `REGISTERED` | Studionet Explorer and Studio finalized read |
| Live safe-branch caller `0x21b451...7e2eC7` | Assess unavailable record `NCT99999999` | `assess` | `0xa25b2654...1adc7b4b` | `FINALIZED` / `SUCCESS`, consensus accepted | `UNRESOLVED`, not certified, `SOURCE_HTTP_ERROR`, source unsafe; ID and NCT reads match | Studionet Explorer and Studio finalized reads |

This matrix intentionally distinguishes direct-test proof from live-chain evidence. Full values are in `deployments/studionet.json`.
