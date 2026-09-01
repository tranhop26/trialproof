import { describe, expect, test } from "vitest";

import { runSample, type SampleClient } from "../run-sample.js";
import type { DeploymentManifest } from "../write-manifest.js";


const address = "0x1111111111111111111111111111111111111111";
const privateKey = `0x${"1".repeat(64)}` as const;
const registerHash = `0x${"a".repeat(64)}`;
const assessHash = `0x${"b".repeat(64)}`;
const manifest: DeploymentManifest = {
  address,
  chainId: 4221,
  dependencyHash: "abc",
  deployedAt: "2026-08-25T10:00:00.000Z",
  deployer: "0x2222222222222222222222222222222222222222",
  initialAssessmentCount: 0,
  network: "testnet-bradbury",
  sourceBytes: 100,
  sourceSha256: "c".repeat(64),
  transactionHash: `0x${"d".repeat(64)}`,
  version: "trialproof/1.1.0",
};
const finalReceipt = { executionStatus: "FINISHED_WITH_RETURN", finalized: true };
const stored = {
  assessment_id: "1",
  attempt: 1,
  certified: true,
  evidence_hash: `0x${"e".repeat(64)}`,
  nct_id: "NCT01234567",
  resolution: { verdict: "DISCLOSURE_COMPLETE" },
  state: "DISCLOSURE_COMPLETE",
};


function client(overrides: Partial<SampleClient> = {}): SampleClient {
  let writes = 0;
  let reads = 0;
  return {
    getCallerAddress: async () => address,
    readAssessmentByNctId: async () =>
      JSON.stringify(
        ++reads === 1
          ? {
              ...stored,
              certified: false,
              evidence_hash: "",
              resolution: {},
              state: "REGISTERED",
            }
          : stored,
      ),
    waitForReceipt: async () => finalReceipt,
    writeContract: async () => (++writes === 1 ? registerHash : assessHash),
    ...overrides,
  };
}


function environment(name: string): string | undefined {
  return {
    GENLAYER_PRIVATE_KEY: privateKey,
    TRIALPROOF_SAMPLE_CONFIRM: "RUN_TRIALPROOF_SAMPLE",
  }[name];
}


describe("runSample", () => {
  test("requires explicit live mode and confirmation sentinel", async () => {
    await expect(
      runSample({ client: client(), getEnv: environment, manifest, nctId: "NCT01234567" }),
    ).rejects.toThrow("SAMPLE_MUTATION_DISABLED");
    await expect(
      runSample({
        client: client(),
        getEnv: (name) => (name === "GENLAYER_PRIVATE_KEY" ? privateKey : undefined),
        manifest,
        mutationMode: "live",
        nctId: "NCT01234567",
      }),
    ).rejects.toThrow("SAMPLE_CONFIRMATION_REQUIRED");
  });

  test.each([
    [client(), "NCT01234567", "SAMPLE_CANDIDATE_VERSION_MISMATCH", { ...manifest, version: "trialproof/1.0.1" }],
    [client(), "NCT01234567", "SAMPLE_INVALID_SOURCE_IDENTITY", { ...manifest, sourceSha256: "" }],
    [client(), "NCT123", "SAMPLE_INVALID_NCT_ID"],
    [client({ getCallerAddress: async () => "invalid" }), "NCT01234567", "SAMPLE_INVALID_WALLET"],
    [client({ waitForReceipt: async () => ({ finalized: false, executionStatus: "PENDING" }) }), "NCT01234567", "SAMPLE_FINALITY_OR_EXECUTION_FAILED"],
    [client({ readAssessmentByNctId: async () => JSON.stringify({ ...stored, nct_id: "NCT76543210" }) }), "NCT01234567", "SAMPLE_READBACK_MISMATCH"],
  ])("rejects unsafe sample evidence", async (candidateClient, nctId, message, candidateManifest = manifest) => {
    await expect(
      runSample({
        client: candidateClient,
        getEnv: environment,
        manifest: candidateManifest,
        mutationMode: "live",
        nctId,
      }),
    ).rejects.toThrow(message);
  });

  test("returns transaction finality and state only after authoritative readback", async () => {
    const report = await runSample({
      client: client(),
      getEnv: environment,
      manifest,
      mutationMode: "live",
      nctId: "NCT01234567",
    });
    expect(report.registrationTransactionHash).toBe(registerHash);
    expect(report.assessmentTransactionHash).toBe(assessHash);
    expect(report.registrationFinalized).toBe(true);
    expect(report.assessmentFinalized).toBe(true);
    expect(report.readback.state).toBe("DISCLOSURE_COMPLETE");
  });

  test("rejects an unknown state before sending the assess mutation", async () => {
    await expect(
      runSample({
        client: client({
          readAssessmentByNctId: async () =>
            JSON.stringify({ ...stored, certified: false, resolution: { verdict: "FUTURE" }, state: "FUTURE" }),
        }),
        getEnv: environment,
        manifest,
        mutationMode: "live",
        nctId: "NCT01234567",
      }),
    ).rejects.toThrow("SAMPLE_READBACK_STATE_INVALID");
  });
});
