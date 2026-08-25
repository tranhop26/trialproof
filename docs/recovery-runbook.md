# Frozen-contract recovery runbook

1. Preserve the transaction hash, receipt, manifest, source hash, network, wallet address, error text, and observed time. Never copy a private key or token into the incident record.
2. Distinguish transaction submission, pending consensus, `FINALIZED`, execution `FINISHED_WITH_RETURN`, and execution failure. A submitted hash is not success.
3. Run `scripts/readback.ts` and compare deployed code, frozen schema, version, assessment count, NCT ID, state, verdict, `certified`, evidence hash, attempt, and revision.
4. If an assessment transaction did not reach a valid state change, leave contract state authoritative. At the original deadline, call `expire_assessment` to record `UNRESOLVED`.
5. For `ACTION_REQUIRED`, `REQUEST_MORE_INFO`, or `UNRESOLVED`, wait until `next_refresh_at` and call `refresh`. Do not reuse a prior action domain or exceed three attempts.
6. After three unsuccessful attempts, call `close_after_max_attempts`. Never rewrite a verdict off-chain.
7. For a terminal assessment, do not retry or attempt administrative repair; no such route exists.
8. If source, schema, version, or manifest mismatches, quarantine the deployment. Review and deploy a new frozen version only after a new action-time wallet confirmation. Preserve the old contract as read-only audit history.
9. Record confirmed evidence in `evidence/test-results.md` and `evidence/proof-matrix.md`.
