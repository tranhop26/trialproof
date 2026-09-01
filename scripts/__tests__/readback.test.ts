import { describe, expect, test } from "vitest";

import { runReadback, type ReadbackClient } from "../readback.js";
import type { DeploymentManifest } from "../write-manifest.js";


const source = Buffer.from("# dependency\ncontract\n");
const hash = "80118aa8afa0c5c6dc89cdfe1ec2eb1c146a3e7fab8e2b763d63652d93adc247";
const address = "0x1111111111111111111111111111111111111111";
const methods = {
  assess: {}, close_after_max_attempts: {}, expire_assessment: {}, get_assessment: {},
  get_assessment_by_nct_id: {}, get_assessment_count: {}, get_assessment_ids_page: {},
  get_version: {}, refresh: {}, register_study: {},
};
const assessment = {
  assessment_id: "1",
  attempt: 1,
  certified: true,
  evidence_hash: `0x${"a".repeat(64)}`,
  nct_id: "NCT01234567",
  resolution: { verdict: "DISCLOSURE_COMPLETE" },
  state: "DISCLOSURE_COMPLETE",
};
const manifest: DeploymentManifest = {
  address,
  chainId: 4221,
  dependencyHash: "abc",
  deployedAt: "2026-08-25T10:00:00.000Z",
  deployer: "0x2222222222222222222222222222222222222222",
  initialAssessmentCount: 0,
  network: "testnet-bradbury",
  sourceBytes: source.byteLength,
  sourceSha256: hash,
  transactionHash: `0x${"b".repeat(64)}`,
  version: "trialproof/1.1.0",
};


function client(overrides: Partial<ReadbackClient> = {}): ReadbackClient {
  return {
    getCodeSchema: async () => ({ methods }),
    getRuntimeSchema: async () => ({ methods }),
    readAssessment: async () => JSON.stringify(assessment),
    readAssessmentCount: async () => 1,
    readCurrentCode: async () => source,
    readVersion: async () => "trialproof/1.1.0",
    ...overrides,
  };
}


describe("runReadback", () => {
  test("verifies a 1.1.0 manifest and runtime with authoritative assessment state", async () => {
    const report = await runReadback({
      assessmentId: "1",
      client: client(),
      expectedNctId: "NCT01234567",
      expectedSourceBytes: source,
      expectedVersion: "trialproof/1.1.0",
      manifest,
    });
    expect(report.sourceMatches).toBe(true);
    expect(report.assessment?.state).toBe("DISCLOSURE_COMPLETE");
    expect(report.assessment?.certified).toBe(true);
    expect(report.version).toBe("trialproof/1.1.0");
  });

  test.each([
    {
      ...assessment,
      certified: false,
      evidence_hash: "",
      resolution: {},
      state: "REGISTERED",
    },
    {
      ...assessment,
      certified: false,
      resolution: { verdict: "ACTION_REQUIRED" },
      state: "CLOSED_UNCERTIFIED",
    },
  ])("accepts contract states with their valid certification semantics", async (candidateAssessment) => {
    const report = await runReadback({
      assessmentId: "1",
      client: client({ readAssessment: async () => JSON.stringify(candidateAssessment) }),
      expectedNctId: "NCT01234567",
      expectedSourceBytes: source,
      expectedVersion: "trialproof/1.1.0",
      manifest,
    });
    expect(report.assessment?.state).toBe(candidateAssessment.state);
  });

  test.each([
    [{ ...manifest, chainId: 1 }, client(), "MANIFEST_CHAIN_ID_MISMATCH"],
    [{ ...manifest, sourceSha256: "0".repeat(64) }, client(), "SOURCE_HASH_MISMATCH"],
    [manifest, client({ readCurrentCode: async () => Buffer.from("different") }), "DEPLOYED_CODE_MISMATCH"],
    [manifest, client({ readVersion: async () => "trialproof/1.0.1" }), "VERSION_MISMATCH"],
    [manifest, client({ getRuntimeSchema: async () => ({ methods: {} }) }), "RUNTIME_SCHEMA_SURFACE_MISMATCH"],
    [manifest, client({ readAssessment: async () => JSON.stringify({ ...assessment, nct_id: "NCT76543210" }) }), "ASSESSMENT_NCT_MISMATCH"],
    [manifest, client({ readAssessment: async () => JSON.stringify({ ...assessment, state: "ACTION_REQUIRED" }) }), "ASSESSMENT_CERTIFICATION_INCONSISTENT"],
    [{ ...manifest, version: "trialproof/1.0.1" }, client(), "MANIFEST_VERSION_MISMATCH"],
    [manifest, client({ readAssessment: async () => JSON.stringify({ ...assessment, certified: false, resolution: { verdict: "FUTURE" }, state: "FUTURE" }) }), "ASSESSMENT_STATE_INVALID"],
  ])("rejects mismatched deployment or state evidence", async (candidateManifest, candidateClient, message) => {
    await expect(
      runReadback({
        assessmentId: "1",
        client: candidateClient,
        expectedNctId: "NCT01234567",
        expectedSourceBytes: source,
        expectedVersion: "trialproof/1.1.0",
        manifest: candidateManifest,
      }),
    ).rejects.toThrow(message);
  });
});
