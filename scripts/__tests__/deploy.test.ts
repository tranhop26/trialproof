import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, test } from "vitest";

import { runDeployment, type DeploymentClient } from "../../deploy/001_deploy_trialproof.js";


const privateKey = `0x${"1".repeat(64)}` as const;
const address = "0x1111111111111111111111111111111111111111";
const transactionHash = `0x${"2".repeat(64)}`;
const expectedMethods = {
  assess: {}, close_after_max_attempts: {}, expire_assessment: {}, get_assessment: {},
  get_assessment_by_nct_id: {}, get_assessment_count: {}, get_assessment_ids_page: {},
  get_version: {}, refresh: {}, register_study: {},
};


function client(overrides: Partial<DeploymentClient> = {}): DeploymentClient {
  return {
    deployContract: async () => ({
      address,
      executionStatus: "FINISHED_WITH_RETURN",
      finalized: true,
      transactionHash,
    }),
    getChainId: async () => 4221,
    getCodeSchema: async () => ({ methods: expectedMethods }),
    getDeployerAddress: async () => address,
    getRuntimeSchema: async () => ({ methods: expectedMethods }),
    readAssessmentCount: async () => 0,
    readVersion: async () => "trialproof/1.0.1",
    ...overrides,
  };
}


async function setup() {
  const directory = await mkdtemp(join(tmpdir(), "trialproof-deploy-"));
  const artifactPath = join(directory, "trial_proof.py");
  const manifestPath = join(directory, "bradbury.json");
  await writeFile(
    artifactPath,
    '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }\nclass TrialProof: pass\n',
  );
  return { artifactPath, manifestPath };
}


function environment(name: string): string | undefined {
  return {
    GENLAYER_PRIVATE_KEY: privateKey,
    TRIALPROOF_DEPLOY_CONFIRM: "DEPLOY_TRIALPROOF",
  }[name];
}


describe("runDeployment", () => {
  test("requires explicit live mode", async () => {
    const paths = await setup();
    await expect(
      runDeployment({ ...paths, client: client(), getEnv: environment }),
    ).rejects.toThrow("DEPLOY_MUTATION_DISABLED");
  });

  test.each([
    [() => undefined, "DEPLOY_INVALID_PRIVATE_KEY"],
    [(name: string) => (name === "GENLAYER_PRIVATE_KEY" ? privateKey : undefined), "DEPLOY_CONFIRMATION_REQUIRED"],
  ])("rejects missing authority", async (getEnv, message) => {
    const paths = await setup();
    await expect(
      runDeployment({ ...paths, client: client(), getEnv, mutationMode: "live" }),
    ).rejects.toThrow(message);
  });

  test.each([
    [client({ getChainId: async () => 1 }), "DEPLOY_WRONG_CHAIN"],
    [client({ getDeployerAddress: async () => "invalid" }), "DEPLOY_INVALID_WALLET"],
    [client({ deployContract: async () => ({ address, executionStatus: "PENDING", finalized: false, transactionHash }) }), "DEPLOY_FINALITY_OR_EXECUTION_FAILED"],
    [client({ readVersion: async () => "wrong" }), "DEPLOY_VERSION_MISMATCH"],
    [client({ readAssessmentCount: async () => 1 }), "DEPLOY_NONZERO_INITIAL_STATE"],
    [client({ getRuntimeSchema: async () => ({ methods: {} }) }), "DEPLOY_SCHEMA_SURFACE_MISMATCH"],
  ])("rejects unsafe deployment evidence", async (unsafeClient, message) => {
    const paths = await setup();
    await expect(
      runDeployment({
        ...paths,
        client: unsafeClient,
        getEnv: environment,
        mutationMode: "live",
        verifyArtifactFreshness: async () => undefined,
      }),
    ).rejects.toThrow(message);
  });

  test("writes a source-bound manifest only after finalized successful readback", async () => {
    const paths = await setup();
    const manifest = await runDeployment({
      ...paths,
      client: client(),
      getEnv: environment,
      mutationMode: "live",
      now: () => "2026-08-25T10:00:00.000Z",
      verifyArtifactFreshness: async () => undefined,
    });
    expect(manifest.address).toBe(address);
    expect(manifest.transactionHash).toBe(transactionHash);
    expect(manifest.initialAssessmentCount).toBe(0);
    expect(manifest.sourceSha256).toMatch(/^[0-9a-f]{64}$/);
  });
});
