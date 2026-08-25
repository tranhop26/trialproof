import { readFile } from "node:fs/promises";

import { assertExpectedSchemaSurface } from "../deploy/001_deploy_trialproof.js";
import { sha256, type DeploymentManifest } from "./write-manifest.js";


type ContractSchema = { methods?: Record<string, unknown> };

export type AssessmentReadback = {
  assessment_id: string;
  attempt: number;
  certified: boolean;
  evidence_hash: string;
  nct_id: string;
  resolution: { verdict?: string };
  state: string;
  [key: string]: unknown;
};

export type ReadbackClient = {
  getCodeSchema: (source: Uint8Array) => Promise<ContractSchema>;
  getRuntimeSchema: (address: string) => Promise<ContractSchema>;
  readAssessment: (address: string, assessmentId: string) => Promise<string>;
  readAssessmentCount: (address: string) => Promise<number>;
  readCurrentCode: (address: string) => Promise<string | Uint8Array>;
  readVersion: (address: string) => Promise<string>;
};

export type ReadbackOptions = {
  assessmentId?: string;
  client: ReadbackClient;
  expectedNctId?: string;
  expectedSourceBytes: Uint8Array;
  expectedVersion: string;
  manifest: DeploymentManifest;
};

export type ReadbackReport = {
  address: string;
  assessment?: AssessmentReadback;
  assessmentCount: number;
  sourceMatches: boolean;
  sourceSha256: string;
  version: string;
};

const ADDRESS = /^0x[0-9a-fA-F]{40}$/;
const TRANSACTION = /^0x[0-9a-fA-F]{64}$/;


function normalizeTransport(source: string | Uint8Array): Buffer {
  const text = typeof source === "string" ? source : Buffer.from(source).toString("utf8");
  return Buffer.from(text.replace(/\r\n/gu, "\n"), "utf8");
}

function validateManifest(manifest: DeploymentManifest, expectedSource: Uint8Array): void {
  if (manifest.network !== "testnet-bradbury") {
    throw new Error("MANIFEST_NETWORK_MISMATCH");
  }
  if (manifest.chainId !== 4221) {
    throw new Error("MANIFEST_CHAIN_ID_MISMATCH");
  }
  if (!ADDRESS.test(manifest.address)) {
    throw new Error("MANIFEST_INVALID_ADDRESS");
  }
  if (!TRANSACTION.test(manifest.transactionHash)) {
    throw new Error("MANIFEST_INVALID_TRANSACTION_HASH");
  }
  if (manifest.sourceBytes !== expectedSource.byteLength) {
    throw new Error("MANIFEST_SOURCE_BYTES_MISMATCH");
  }
}

function parseAssessment(
  value: string,
  assessmentId: string,
  expectedNctId?: string,
): AssessmentReadback {
  let assessment: AssessmentReadback;
  try {
    assessment = JSON.parse(value) as AssessmentReadback;
  } catch {
    throw new Error("ASSESSMENT_MALFORMED");
  }
  if (!assessment || assessment.assessment_id !== assessmentId) {
    throw new Error("ASSESSMENT_ID_MISMATCH");
  }
  if (expectedNctId && assessment.nct_id !== expectedNctId) {
    throw new Error("ASSESSMENT_NCT_MISMATCH");
  }
  const shouldBeCertified = assessment.state === "DISCLOSURE_COMPLETE";
  if (
    assessment.certified !== shouldBeCertified ||
    assessment.resolution?.verdict !== assessment.state
  ) {
    throw new Error("ASSESSMENT_CERTIFICATION_INCONSISTENT");
  }
  if (!/^0x[0-9a-f]{64}$/u.test(assessment.evidence_hash)) {
    throw new Error("ASSESSMENT_EVIDENCE_HASH_INVALID");
  }
  return assessment;
}


export async function runReadback(options: ReadbackOptions): Promise<ReadbackReport> {
  const expectedSource = Buffer.from(options.expectedSourceBytes);
  validateManifest(options.manifest, expectedSource);
  const sourceHash = sha256(expectedSource);
  if (sourceHash !== options.manifest.sourceSha256) {
    throw new Error("SOURCE_HASH_MISMATCH");
  }
  const currentCode = await options.client.readCurrentCode(options.manifest.address);
  const sourceMatches =
    Buffer.compare(normalizeTransport(currentCode), normalizeTransport(expectedSource)) === 0;
  if (!sourceMatches) {
    throw new Error("DEPLOYED_CODE_MISMATCH");
  }
  try {
    assertExpectedSchemaSurface(await options.client.getCodeSchema(expectedSource));
  } catch {
    throw new Error("CODE_SCHEMA_SURFACE_MISMATCH");
  }
  try {
    assertExpectedSchemaSurface(
      await options.client.getRuntimeSchema(options.manifest.address),
    );
  } catch {
    throw new Error("RUNTIME_SCHEMA_SURFACE_MISMATCH");
  }
  const version = await options.client.readVersion(options.manifest.address);
  if (version !== options.expectedVersion || version !== options.manifest.version) {
    throw new Error("VERSION_MISMATCH");
  }
  const assessmentCount = await options.client.readAssessmentCount(options.manifest.address);
  const assessment = options.assessmentId
    ? parseAssessment(
        await options.client.readAssessment(options.manifest.address, options.assessmentId),
        options.assessmentId,
        options.expectedNctId,
      )
    : undefined;
  return {
    address: options.manifest.address,
    assessment,
    assessmentCount,
    sourceMatches,
    sourceSha256: sourceHash,
    version,
  };
}


async function createLiveClient(privateKey: `0x${string}`): Promise<ReadbackClient> {
  const [{ createAccount, createClient }, { testnetBradbury }] = await Promise.all([
    import("genlayer-js"),
    import("genlayer-js/chains"),
  ]);
  const account = createAccount(privateKey);
  const client = createClient({ account, chain: testnetBradbury });
  return {
    getCodeSchema: async (source) => client.getContractSchemaForCode(source),
    getRuntimeSchema: async (address) => client.getContractSchema(address as `0x${string}`),
    readAssessment: async (address, assessmentId) =>
      String(
        await client.readContract({
          address: address as `0x${string}`,
          args: [assessmentId],
          functionName: "get_assessment",
          jsonSafeReturn: true,
        }),
      ),
    readAssessmentCount: async (address) =>
      Number(
        await client.readContract({
          address: address as `0x${string}`,
          args: [],
          functionName: "get_assessment_count",
          jsonSafeReturn: true,
        }),
      ),
    readCurrentCode: async (address) => client.getContractCode(address as `0x${string}`),
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
  const manifestPath = process.argv[2];
  if (!manifestPath) throw new Error("READBACK_MANIFEST_PATH_REQUIRED");
  const privateKey = process.env.GENLAYER_PRIVATE_KEY as `0x${string}` | undefined;
  if (!privateKey) throw new Error("READBACK_PRIVATE_KEY_REQUIRED");
  const manifest = JSON.parse(await readFile(manifestPath, "utf8")) as DeploymentManifest;
  const source = await readFile("deploy/source/trial_proof.py");
  const report = await runReadback({
    assessmentId: process.argv[3],
    client: await createLiveClient(privateKey),
    expectedNctId: process.argv[4],
    expectedSourceBytes: source,
    expectedVersion: "trialproof/1.0.0",
    manifest,
  });
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}


if (process.argv[1]?.endsWith("readback.ts") || process.argv[1]?.endsWith("readback.js")) {
  void main().catch((error: unknown) => {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  });
}
