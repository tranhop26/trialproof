# Proof matrix

Current verified repository commit: `7ec17582e82893da85b6ff0349fac6e5b78325ec`.
Exact `trialproof/1.1.0` deployment artifact SHA-256:
`8b1eac2585f6c280506c3609c80103612fb75cd4e8bef0e00234bba2851db13c`.

| Actor | Action | Contract method | Transaction hash | `FINALIZED` / `SUCCESS` | Readback | Source/test |
|---|---|---|---|---|---|---|
| Live deployer `0x21b451...7e2eC7` | Deploy exact `trialproof/1.1.0` artifact | deployment | [`0x8f8c0a...c50233`](https://explorer-studio.genlayer.com/tx/0x8f8c0a74f51b2fa53df6341bba31991687c4c22f0cf979777d9d37e7ccc50233) | `FINALIZED` / `SUCCESS` | Contract [`0xa13693E7...7b221`](https://explorer-studio.genlayer.com/address/0xa13693E7A524Bff515227e48256400d1cB67b221); chain `61999`; version `trialproof/1.1.0`; count `0`; source hash matches | `deployments/studionet-v1.1.0.json`; `deploy/source/trial_proof.py`; reproducible-build check |
| Live sample caller `0x21b451...7e2eC7` | Register `NCT04516746` on 1.1.0 | `register_study` | [`0xf5396825...f6af55`](https://explorer-studio.genlayer.com/tx/0xf5396825e1a23787071a34ea5c3b896bd3e3d7d4d2a0051378577a248ff6af55) | `FINALIZED` / `SUCCESS`, `MAJORITY_AGREE` | assessment `1`, `REGISTERED`, count `1`, registrant matches caller | Studionet transaction receipt and contract readback by NCT ID |
| Live sample caller `0x21b451...7e2eC7` | Assess `NCT04516746` on 1.1.0 | `assess` | [`0xa52f883c...15f514`](https://explorer-studio.genlayer.com/tx/0xa52f883c39aad1edf2dd00c9fe18b6ecb4445c4637792b16e2b1b3eb1515f514) | `FINALIZED` / `SUCCESS`, `MAJORITY_AGREE` | `DISCLOSURE_COMPLETE`, certified; 4 registered / 4 eligible reported `PRIMARY`; all matched / none missing; source safe and fresh; ID and NCT reads identical | Studionet transaction receipt; live contract readback; `tests/direct/test_evidence.py`; `tests/direct/test_consensus.py` |
| Live safe-branch caller `0x21b451...7e2eC7` | Register unavailable `NCT99999999` on 1.1.0 | `register_study` | [`0x9022f59c...54e0ecf`](https://explorer-studio.genlayer.com/tx/0x9022f59cf30a938f8c906e4c2ff8b339f64bc7b8ff26f7b1dd3ea4e6354e0ecf) | `FINALIZED` / `SUCCESS`, `MAJORITY_AGREE` | assessment `2`, `REGISTERED`, count `2`, registrant matches caller | Studionet transaction receipt and contract readback by NCT ID |
| Live safe-branch caller `0x21b451...7e2eC7` | Assess unavailable `NCT99999999` on 1.1.0 | `assess` | [`0x00b9073e...f35451`](https://explorer-studio.genlayer.com/tx/0x00b9073e7e467800f43b4f252a0188342abdfb8881e92496e66bf28b8cf35451) | `FINALIZED` / `SUCCESS`, `MAJORITY_AGREE` | `UNRESOLVED`, not certified, `SOURCE_HTTP_ERROR`; source unsafe/not fresh; attempt/revision `1`; ID and NCT reads identical | Studionet transaction receipt; live contract readback; `tests/direct/test_consensus.py` |
| Unrelated direct-test address | Certify only a matching `PRIMARY` reported outcome with a non-empty nested measurement value | `assess` | direct test; no live hash | direct VM success | `DISCLOSURE_COMPLETE`, certified only when all required primary outcomes match valid data | `tests/direct/test_evidence.py`; `tests/direct/test_consensus.py` |
| Unrelated direct-test address | Reject secondary/lowercase-primary outcomes, empty values, and malformed nested measurement structures | `assess` | direct test; no live hash | direct VM success | safe non-certifying result; malformed evidence is unsafe | `tests/direct/test_evidence.py` |
| Unrelated direct-test address | Handle contradictions among `hasResults`, results-posted date, and eligible primary result data | `assess` | direct test; no live hash | direct VM success | `UNRESOLVED`, not certified, `SOURCE_RESULTS_CONTRADICTORY` | `tests/direct/test_evidence.py`; `tests/direct/test_consensus.py` |
| Unrelated direct-test address | Expire unresolved case | `expire_assessment` | direct test; no live hash | direct VM success | `UNRESOLVED`, not certified | `tests/direct/test_liveness.py` |

## Historical live evidence (`trialproof/1.0.1` only)

| Actor | Action | Contract method | Transaction hash | `FINALIZED` / `SUCCESS` | Readback | Source/test |
|---|---|---|---|---|---|---|
| Live deployer `0x21b451...7e2eC7` | Deploy exact `1.0.1` artifact | deployment | [`0xac22c762...18672b`](https://explorer-studio.genlayer.com/tx/0xac22c7627f1cb6c91bf8627b3dd7822cf999906b2079dd748e48e8d71e18672b) | `FINALIZED` / `SUCCESS` | version `1.0.1`, count `0`; Explorer code inspected | `deployments/studionet.json` |
| Live sample caller `0x21b451...7e2eC7` | Register `NCT04516746` | `register_study` | [`0xa47427ed...4d913b`](https://explorer-studio.genlayer.com/tx/0xa47427ede94a6d9e049c28239935a22ef495825bacaa754a0fc81493f54d913b) | `FINALIZED` / `SUCCESS` | assessment `1`, `REGISTERED` | `deployments/studionet.json` |
| Live sample caller `0x21b451...7e2eC7` | Assess `NCT04516746` | `assess` | [`0xb3c07509...214aa5`](https://explorer-studio.genlayer.com/tx/0xb3c07509855e70e985225a28cdb6d65a63c5ca15ff28ce586553f83e12214aa5) | `FINALIZED` / `SUCCESS`, consensus accepted | `DISCLOSURE_COMPLETE`, certified, 4 matched / 0 missing | Studio finalized reads by assessment and NCT ID |
| Live safe-branch caller `0x21b451...7e2eC7` | Register unavailable record `NCT99999999` | `register_study` | [`0x0e1ded7c...d20934`](https://explorer-studio.genlayer.com/tx/0x0e1ded7c1f9ba0e8bada2f13339a621dadb0f7e75c045131fc7fc1a227d20934) | `FINALIZED` / `SUCCESS` | assessment `2`, `REGISTERED` | `deployments/studionet.json` |
| Live safe-branch caller `0x21b451...7e2eC7` | Assess unavailable record `NCT99999999` | `assess` | [`0xa25b2654...dc7b4b`](https://explorer-studio.genlayer.com/tx/0xa25b2654959226167b2bd6be6bf88a93f82e7e0c036576170cf24b291adc7b4b) | `FINALIZED` / `SUCCESS`, consensus accepted | `UNRESOLVED`, not certified, `SOURCE_HTTP_ERROR`; assessment and NCT reads match | `deployments/studionet.json`; Studionet Explorer |

The two sections are deliberately separated: the current 1.1.0 deployment,
happy-path, and unavailable-source safe-branch rows prove deployed-source
correspondence and live runtime behavior. Local and CI regression rows cover
the full admin-requested edge-case logic, including exact contradictory
`hasResults`/results-posted/data combinations that cannot safely be fabricated
against the independent live source. The historical 1.0.1 transactions do not
prove 1.1.0 runtime behavior.
