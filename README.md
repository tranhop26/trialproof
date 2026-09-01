# TrialProof

TrialProof is an independent GenLayer Intelligent Contract that makes an authoritative on-chain assessment of whether a ClinicalTrials.gov record reports results for every registered primary outcome.

Historical verified Studionet deployment (`trialproof/1.0.1`): [contract](https://explorer-studio.genlayer.com/address/0x1354c6A89f92F9ccE45d7aAdC2b9bC372b51b158). Its exact deployment and sample evidence is recorded immutably in `deployments/studionet.json`.

`trialproof/1.1.0` is the fixed local candidate. It is not deployed or source-verified on Studionet; a new finalized deployment manifest is required before associating it with any contract address or live transaction.

Historical `trialproof/1.0.1` live evidence: [deployment transaction](https://explorer-studio.genlayer.com/tx/0xac22c7627f1cb6c91bf8627b3dd7822cf999906b2079dd748e48e8d71e18672b), happy-path [registration](https://explorer-studio.genlayer.com/tx/0xa47427ede94a6d9e049c28239935a22ef495825bacaa754a0fc81493f54d913b) and [assessment](https://explorer-studio.genlayer.com/tx/0xb3c07509855e70e985225a28cdb6d65a63c5ca15ff28ce586553f83e12214aa5), plus unavailable-source safe-branch [registration](https://explorer-studio.genlayer.com/tx/0x0e1ded7c1f9ba0e8bada2f13339a621dadb0f7e75c045131fc7fc1a227d20934) and [assessment](https://explorer-studio.genlayer.com/tx/0xa25b2654959226167b2bd6be6bf88a93f82e7e0c036576170cf24b291adc7b4b). These transactions do not evidence the undeployed `trialproof/1.1.0` candidate.

It is intentionally narrow: one contract, one disclosure workflow, safe retry/timeout branches, deployment/readback tooling, and no frontend or financial mechanism.

## Decision and consequence

The contract records one of four validator-derived decisions:

- `DISCLOSURE_COMPLETE`: every registered primary outcome has a semantically corresponding reported outcome with result data.
- `ACTION_REQUIRED`: the accessible official record lacks at least one required primary result.
- `REQUEST_MORE_INFO`: the official record is fresh and accessible but omits fields required for a decision.
- `UNRESOLVED`: evidence is unavailable, stale, malformed, contradictory, identity-mismatched, or consensus/execution cannot safely finish.

Only `DISCLOSURE_COMPLETE` sets `certified=true`. The caller supplies only an NCT ID. The contract constructs the official ClinicalTrials.gov endpoints and neither caller nor deployer can provide a URL, evidence body, validator answer, or verdict.

TrialProof assesses registry disclosure completeness. It does not determine medical efficacy, trial quality, legal compliance, or participant safety.

## Trust and evidence summary

Sponsors and reviewers cannot rely on each other's narrative. Relayers cannot be trusted to order calls correctly. A single validator cannot be trusted to interpret changing web content alone.

The contract binds evidence to `clinicaltrials.gov`, NCT ID, official sponsor identity, API version and `dataTimestamp`, observation time, policy/workflow version, chain, contract, assessment ID, revision, attempt, and canonical snapshot hash. API data older than 120 hours is unsafe.

Validators independently fetch and assess the same official record. Equivalence compares the verdict, identities, reason codes, counts, matched/missing outcome-index sets, source safety/freshness, API timestamp, and evidence hash. Free-form rationale is not compared.

See [architecture](docs/architecture.md) for the complete state table and trust matrix.

## Contract classification

`INTENTIONALLY_FROZEN`. The ABI has no owner, admin, upgrader, source setter, policy setter, verdict setter, payable method, or withdrawal route. API or policy changes require a new reviewed deployment; the old contract remains immutable and readable.

## Requirements and install

- Python 3.12 or newer
- Node.js 22 or newer
- npm

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
npm ci
```

Copy `.env.example` to an untracked `.env` only when a live network action is required. Never commit or print its values.

## Format, lint, and offline tests

```powershell
ruff format --check contracts tests scripts
$env:PYTHONIOENCODING = "utf-8"
genvm-lint check contracts/trial_proof.py
python scripts/build_bradbury_contract.py --check
pytest tests/direct tests/tooling -v
pytest tests/integration -v
npm test
npm run typecheck
```

The RPC lifecycle test reports `TRIALPROOF_RPC_UNAVAILABLE` as skipped when no configured GenLayer RPC is reachable. A skip is not live integration evidence.

To run against a configured environment:

```powershell
pytest tests/integration/test_trialproof_rpc.py -v --network localnet
pytest tests/integration/test_trialproof_rpc.py -v --network testnet_bradbury --config gltest.config.bradbury.yaml
```

## Deployment artifact

`contracts/trial_proof.py` is the readable source. `deploy/source/trial_proof.py` is the exact size-bounded deployment artifact.

```powershell
python scripts/build_bradbury_contract.py
python scripts/build_bradbury_contract.py --check
```

The check must pass before deployment. Never edit the artifact directly.

## Deployment

Dry-run is the default and does not mutate the network:

```powershell
npx tsx deploy/001_deploy_trialproof.ts
```

Before live deployment, inspect the Git identity, remote, network chain ID, derived deployment wallet, balance, artifact hash, and exact proposed mutation. Stop and obtain action-time confirmation for that wallet and action.

After confirmation, provide the private key only through the local process environment:

```powershell
$env:GENLAYER_PRIVATE_KEY = "<local secret>"
$env:TRIALPROOF_DEPLOY_CONFIRM = "DEPLOY_TRIALPROOF"
npx tsx deploy/001_deploy_trialproof.ts --live
```

The guarded script requires Bradbury chain ID `4221`, an exact frozen schema, current artifact, source below 50,000 bytes, `FINALIZED`, execution `FINISHED_WITH_RETURN`, version `trialproof/1.1.0`, and zero initial assessments. It writes `deployments/bradbury.json` only after those checks pass.

## Sample transaction and readback

Dry-run:

```powershell
npx tsx scripts/run-sample.ts
```

After the same action-time wallet confirmation process:

```powershell
$env:TRIALPROOF_SAMPLE_CONFIRM = "RUN_TRIALPROOF_SAMPLE"
npx tsx scripts/run-sample.ts deployments/bradbury.json NCT04516746 --live
npx tsx scripts/readback.ts deployments/bradbury.json 1 NCT04516746
```

No `trialproof/1.1.0` live sample or current API preflight is recorded. Before any user-confirmed 1.1.0 deployment or sample action, fetch the official source again and apply the candidate's eligible-`PRIMARY` and nested-measurement validation locally. The historical 1.0.1 transactions above do not prove 1.1.0 source behavior. A 1.1.0 result is established only after its own transaction is `FINALIZED`, execution is `FINISHED_WITH_RETURN`, and its contract state is read back. Submission of a transaction hash alone is not success.

## Public methods

- `register_study(nct_id)`
- `assess(assessment_id)`
- `refresh(assessment_id)`
- `expire_assessment(assessment_id)`
- `close_after_max_attempts(assessment_id)`
- `get_assessment(assessment_id)`
- `get_assessment_by_nct_id(nct_id)`
- `get_assessment_count()`
- `get_assessment_ids_page(start, limit)`
- `get_version()`

Registration, assessment, refresh, expiry, and closure are permissionless because none can select the result or transfer value. Duplicate NCT registration, early refresh, excessive retries, replayed action domains, and terminal-state writes are rejected.

## Known limitations

- ClinicalTrials.gov availability, schema, and anti-automation behavior can cause safe `UNRESOLVED` outcomes.
- Semantic matching is limited to the bounded fields returned by the official API projection.
- One assessment exists per NCT ID and policy version; policy changes require a new frozen deployment.
- No multi-registry cross-check, appeal governance, medical interpretation, or legal determination is provided.
- The immutable `1.0.0` trial instance is superseded because it safely returned `REQUEST_MORE_INFO` after an upstream sponsor-path mismatch. The historical verified deployment is the separate frozen `1.0.1` successor above; `1.1.0` remains an undeployed candidate.

See [recovery runbook](docs/recovery-runbook.md) for failure handling.
