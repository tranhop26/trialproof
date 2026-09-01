import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { readFile, stat } from "node:fs/promises";

import {
  buildDeploymentManifest,
  sha256,
  writeManifestAtomically,
  type DeploymentManifest,
} from "../scripts/write-manifest.js";


type ContractSchema = { methods?: Record<string, unknown> };
type DeployReceipt = {
  address?: string;
  executionStatus: string;
  finalized: boolean;
  transactionHash: string;
};

export type DeploymentClient = {
  deployContract: (args: {
    code: Uint8Array;
    privateKey: `0x${string}`;
  }) => Promise<DeployReceipt>;
  getChainId: () => Promise<number>;
  getCodeSchema: (code: Uint8Array) => Promise<ContractSchema>;
  getDeployerAddress: (privateKey: `0x${string}`) => Promise<string>;
  getRuntimeSchema: (address: string) => Promise<ContractSchema>;
  readAssessmentCount: (address: string) => Promise<number>;
  readVersion: (address: string) => Promise<string>;
};

export type DeploymentOptions = {
  artifactPath: string;
  client: DeploymentClient;
  getEnv?: (name: string) => string | undefined;
  manifestPath: string;
  mutationMode?: "dry-run" | "live";
  now?: () => string;
  verifyArtifactFreshness?: () => Promise<void>;
};

export const EXPECTED_PUBLIC_METHODS = [
  "assess",
  "close_after_max_attempts",
  "expire_assessment",
  "get_assessment",
  "get_assessment_by_nct_id",
  "get_assessment_count",
  "get_assessment_ids_page",
  "get_version",
  "refresh",
  "register_study",
] as const;

const ADDRESS = /^0x[0-9a-fA-F]{40}$/;
const PRIVATE_KEY = /^0x[0-9a-fA-F]{64}$/;
const TRANSACTION = /^0x[0-9a-fA-F]{64}$/;
const SOURCE_LIMIT = 50_000;


function schemaMethods(schema: ContractSchema): string[] {
  return Object.keys(schema.methods ?? {}).sort();
}

export function assertExpectedSchemaSurface(schema: ContractSchema): void {
  const actual = schemaMethods(schema);
  const expected = [...EXPECTED_PUBLIC_METHODS].sort();
  if (actual.join("|") !== expected.join("|")) {
    throw new Error("DEPLOY_SCHEMA_SURFACE_MISMATCH");
  }
}


export async function runDeployment(
  options: DeploymentOptions,
): Promise<DeploymentManifest> {
  if ((options.mutationMode ?? "dry-run") !== "live") {
    throw new Error("DEPLOY_MUTATION_DISABLED");
  }
  const getEnv = options.getEnv ?? ((name: string) => process.env[name]);
  const privateKey = getEnv("GENLAYER_PRIVATE_KEY");
  if (!privateKey || !PRIVATE_KEY.test(privateKey)) {
    throw new Error("DEPLOY_INVALID_PRIVATE_KEY");
  }
  if (getEnv("TRIALPROOF_DEPLOY_CONFIRM") !== "DEPLOY_TRIALPROOF") {
    throw new Error("DEPLOY_CONFIRMATION_REQUIRED");
  }
  if ((await options.client.getChainId()) !== 4221) {
    throw new Error("DEPLOY_WRONG_CHAIN");
  }
  const deployer = await options.client.getDeployerAddress(privateKey as `0x${string}`);
  if (!ADDRESS.test(deployer)) {
    throw new Error("DEPLOY_INVALID_WALLET");
  }
  const artifactStat = await stat(options.artifactPath);
  const code = await readFile(options.artifactPath);
  if (artifactStat.size <= 0 || artifactStat.size >= SOURCE_LIMIT || code.byteLength >= SOURCE_LIMIT) {
    throw new Error("DEPLOY_SOURCE_TOO_LARGE");
  }
  if (!options.verifyArtifactFreshness) {
    throw new Error("DEPLOY_ARTIFACT_FRESHNESS_CHECK_REQUIRED");
  }
  try {
    await options.verifyArtifactFreshness();
  } catch {
    throw new Error("DEPLOY_ARTIFACT_STALE");
  }
  assertExpectedSchemaSurface(await options.client.getCodeSchema(code));
  const receipt = await options.client.deployContract({
    code,
    privateKey: privateKey as `0x${string}`,
  });
  if (!receipt.finalized || receipt.executionStatus !== "FINISHED_WITH_RETURN") {
    throw new Error("DEPLOY_FINALITY_OR_EXECUTION_FAILED");
  }
  if (!receipt.address || !ADDRESS.test(receipt.address)) {
    throw new Error("DEPLOY_INVALID_ADDRESS");
  }
  if (!TRANSACTION.test(receipt.transactionHash)) {
    throw new Error("DEPLOY_INVALID_TRANSACTION_HASH");
  }
  assertExpectedSchemaSurface(await options.client.getRuntimeSchema(receipt.address));
  const version = await options.client.readVersion(receipt.address);
  if (version !== "trialproof/1.1.0") {
    throw new Error("DEPLOY_VERSION_MISMATCH");
  }
  const initialAssessmentCount = await options.client.readAssessmentCount(receipt.address);
  if (initialAssessmentCount !== 0) {
    throw new Error("DEPLOY_NONZERO_INITIAL_STATE");
  }
  const manifest = buildDeploymentManifest({
    address: receipt.address,
    chainId: 4221,
    dependencyHeader: code.toString("utf8").split(/\r?\n/u, 1)[0] ?? "",
    deployedAt: options.now?.() ?? new Date().toISOString(),
    deployer,
    initialAssessmentCount,
    network: "testnet-bradbury",
    sourceBytes: code.byteLength,
    sourceSha256: sha256(code),
    transactionHash: receipt.transactionHash,
    version,
  });
  await writeManifestAtomically(options.manifestPath, manifest);
  return manifest;
}


async function createLiveClient(privateKey: `0x${string}`): Promise<DeploymentClient> {
  const [{ createAccount, createClient }, { testnetBradbury }, types] = await Promise.all([
    import("genlayer-js"),
    import("genlayer-js/chains"),
    import("genlayer-js/types"),
  ]);
  const account = createAccount(privateKey);
  const client = createClient({ account, chain: testnetBradbury });
  const finalized = String(types.TransactionStatus.FINALIZED);
  return {
    deployContract: async ({ code }) => {
      const transactionHash = await client.deployContract({ account, code });
      const receipt = await client.waitForTransactionReceipt({
        hash: transactionHash as never,
        status: types.TransactionStatus.FINALIZED,
      });
      const decoded = receipt.txDataDecoded as { contractAddress?: string } | undefined;
      const data = (receipt.data ?? {}) as {
        contractAddress?: string;
        contract_address?: string;
      };
      return {
        address: decoded?.contractAddress ?? data.contractAddress ?? data.contract_address,
        executionStatus: String(receipt.txExecutionResultName ?? ""),
        finalized:
          String(receipt.statusName) === finalized || receipt.consensus_data?.final === true,
        transactionHash,
      };
    },
    getChainId: async () => Number(client.chain.id),
    getCodeSchema: async (code) => client.getContractSchemaForCode(code),
    getDeployerAddress: async () => account.address,
    getRuntimeSchema: async (address) => client.getContractSchema(address as `0x${string}`),
    readAssessmentCount: async (address) =>
      Number(
        await client.readContract({
          address: address as `0x${string}`,
          args: [],
          functionName: "get_assessment_count",
          jsonSafeReturn: true,
        }),
      ),
    readVersion: async (address) =>
      String(
        await client.readContract({
          address: address as `0x${string}`,
          args: [],
          functionName: "get_version",
          jsonSafeReturn: true,
        }),
      ),
  };
}


async function main(): Promise<void> {
  const live = process.argv.includes("--live");
  if (!live) {
    process.stdout.write(
      `${JSON.stringify({
        action: "dry-run",
        artifactPath: "deploy/source/trial_proof.py",
        manifestPath: "deployments/bradbury.json",
        network: "testnet-bradbury",
        mutationGuard: "set TRIALPROOF_DEPLOY_CONFIRM=DEPLOY_TRIALPROOF and pass --live",
      }, null, 2)}\n`,
    );
    return;
  }
  const privateKey = process.env.GENLAYER_PRIVATE_KEY as `0x${string}` | undefined;
  if (!privateKey || !PRIVATE_KEY.test(privateKey)) {
    throw new Error("DEPLOY_INVALID_PRIVATE_KEY");
  }
  const execFileAsync = promisify(execFile);
  const manifest = await runDeployment({
    artifactPath: "deploy/source/trial_proof.py",
    client: await createLiveClient(privateKey),
    manifestPath: "deployments/bradbury.json",
    mutationMode: "live",
    verifyArtifactFreshness: async () => {
      await execFileAsync("python", ["scripts/build_bradbury_contract.py", "--check"]);
    },
  });
  process.stdout.write(`${JSON.stringify(manifest, null, 2)}\n`);
}


if (process.argv[1]?.endsWith("001_deploy_trialproof.ts") || process.argv[1]?.endsWith("001_deploy_trialproof.js")) {
  void main().catch((error: unknown) => {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  });
}
