import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, test } from "vitest";

import {
  buildDeploymentManifest,
  writeManifestAtomically,
} from "../write-manifest.js";


const input = {
  address: "0x1111111111111111111111111111111111111111",
  chainId: 4221,
  dependencyHeader:
    '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }',
  deployedAt: "2026-08-25T10:00:00.000Z",
  deployer: "0x2222222222222222222222222222222222222222",
  initialAssessmentCount: 0,
  network: "testnet-bradbury",
  sourceBytes: 19364,
  sourceSha256: "a".repeat(64),
  transactionHash: `0x${"b".repeat(64)}`,
  version: "trialproof/1.0.0",
} as const;


describe("buildDeploymentManifest", () => {
  test("binds source, dependency, network, wallet, transaction and zero state", () => {
    expect(buildDeploymentManifest(input)).toEqual({
      address: input.address,
      chainId: 4221,
      dependencyHash: "1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6",
      deployedAt: input.deployedAt,
      deployer: input.deployer,
      initialAssessmentCount: 0,
      network: "testnet-bradbury",
      sourceBytes: 19364,
      sourceSha256: "a".repeat(64),
      transactionHash: input.transactionHash,
      version: "trialproof/1.0.0",
    });
  });

  test.each([
    [{ ...input, address: "0x1234" }, "MANIFEST_INVALID_ADDRESS"],
    [{ ...input, chainId: 1 }, "MANIFEST_WRONG_CHAIN"],
    [{ ...input, sourceSha256: "abc" }, "MANIFEST_INVALID_SOURCE_HASH"],
    [{ ...input, initialAssessmentCount: 1 }, "MANIFEST_NONZERO_INITIAL_STATE"],
  ])("rejects invalid bound fields", (candidate, message) => {
    expect(() => buildDeploymentManifest(candidate)).toThrow(message);
  });
});


describe("writeManifestAtomically", () => {
  test("writes stable JSON and refuses replacement", async () => {
    const directory = await mkdtemp(join(tmpdir(), "trialproof-manifest-"));
    const path = join(directory, "bradbury.json");
    const manifest = buildDeploymentManifest(input);
    await writeManifestAtomically(path, manifest);
    expect(JSON.parse(await readFile(path, "utf8"))).toEqual(manifest);
    await expect(writeManifestAtomically(path, manifest)).rejects.toThrow(
      "MANIFEST_ALREADY_EXISTS",
    );
  });
});
