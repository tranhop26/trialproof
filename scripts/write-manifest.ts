import { createHash, randomUUID } from "node:crypto";
import { access, mkdir, open, rename, unlink, writeFile } from "node:fs/promises";
import { dirname } from "node:path";


export type DeploymentManifest = {
  address: string;
  chainId: number;
  dependencyHash: string;
  deployedAt: string;
  deployer: string;
  initialAssessmentCount: number;
  network: "testnet-bradbury";
  sourceBytes: number;
  sourceSha256: string;
  transactionHash: string;
  version: string;
};

export type DeploymentManifestInput = Omit<DeploymentManifest, "dependencyHash"> & {
  dependencyHeader: string;
};

const ADDRESS = /^0x[0-9a-fA-F]{40}$/;
const TRANSACTION = /^0x[0-9a-fA-F]{64}$/;
const HASH = /^[0-9a-f]{64}$/;
const DEPENDENCY = /py-genlayer:([a-z0-9]+)/;


export function buildDeploymentManifest(
  input: DeploymentManifestInput,
): DeploymentManifest {
  if (!ADDRESS.test(input.address) || !ADDRESS.test(input.deployer)) {
    throw new Error("MANIFEST_INVALID_ADDRESS");
  }
  if (input.chainId !== 4221 || input.network !== "testnet-bradbury") {
    throw new Error("MANIFEST_WRONG_CHAIN");
  }
  if (!TRANSACTION.test(input.transactionHash)) {
    throw new Error("MANIFEST_INVALID_TRANSACTION_HASH");
  }
  if (!HASH.test(input.sourceSha256)) {
    throw new Error("MANIFEST_INVALID_SOURCE_HASH");
  }
  if (!Number.isSafeInteger(input.sourceBytes) || input.sourceBytes <= 0) {
    throw new Error("MANIFEST_INVALID_SOURCE_SIZE");
  }
  if (input.initialAssessmentCount !== 0) {
    throw new Error("MANIFEST_NONZERO_INITIAL_STATE");
  }
  const dependencyHash = input.dependencyHeader.match(DEPENDENCY)?.[1];
  if (!dependencyHash) {
    throw new Error("MANIFEST_INVALID_DEPENDENCY_HEADER");
  }
  if (!input.version || !input.deployedAt) {
    throw new Error("MANIFEST_REQUIRED_FIELDS_MISSING");
  }
  return {
    address: input.address,
    chainId: input.chainId,
    dependencyHash,
    deployedAt: input.deployedAt,
    deployer: input.deployer,
    initialAssessmentCount: input.initialAssessmentCount,
    network: input.network,
    sourceBytes: input.sourceBytes,
    sourceSha256: input.sourceSha256,
    transactionHash: input.transactionHash,
    version: input.version,
  };
}


export async function writeManifestAtomically(
  path: string,
  manifest: DeploymentManifest,
): Promise<void> {
  await mkdir(dirname(path), { recursive: true });
  const lockPath = `${path}.lock`;
  let lock;
  try {
    lock = await open(lockPath, "wx");
  } catch {
    throw new Error("MANIFEST_ALREADY_EXISTS");
  }
  const temporaryPath = `${path}.${randomUUID()}.tmp`;
  try {
    try {
      await access(path);
      throw new Error("MANIFEST_ALREADY_EXISTS");
    } catch (error) {
      if (error instanceof Error && error.message === "MANIFEST_ALREADY_EXISTS") {
        throw error;
      }
    }
    await writeFile(temporaryPath, `${JSON.stringify(manifest, null, 2)}\n`, {
      encoding: "utf8",
      flag: "wx",
    });
    await rename(temporaryPath, path);
  } finally {
    await lock.close();
    await unlink(lockPath).catch(() => undefined);
    await unlink(temporaryPath).catch(() => undefined);
  }
}


export function sha256(source: Uint8Array): string {
  return createHash("sha256").update(source).digest("hex");
}
