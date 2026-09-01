import { readFile } from "node:fs/promises";

import {
  isSupportedNetwork,
  type DeploymentManifest,
} from "./write-manifest.js";


export type SampleReceipt = {
  executionStatus: string;
  finalized: boolean;
};

export type SampleClient = {
  getCallerAddress: (privateKey: `0x${string}`) => Promise<string>;
  readAssessmentByNctId: (address: string, nctId: string) => Promise<string>;
  waitForReceipt: (hash: string) => Promise<SampleReceipt>;
  writeContract: (args: {
    address: string;
    args: string[];
    functionName: "assess" | "register_study";
    privateKey: `0x${string}`;
  }) => Promise<string>;
};

export type SampleOptions = {
  client: SampleClient;
  getEnv?: (name: string) => string | undefined;
  manifest: DeploymentManifest;
  mutationMode?: "dry-run" | "live";
  nctId: string;
};

export type SampleReport = {
  assessmentExecutionStatus: string;
  assessmentFinalized: boolean;
  assessmentTransactionHash: string;
  readback: Record<string, unknown>;
  registrationExecutionStatus: string;
  registrationFinalized: boolean;
  registrationTransactionHash: string;
};

const ADDRESS = /^0x[0-9a-fA-F]{40}$/;
const HASH = /^[0-9a-f]{64}$/;
const PRIVATE_KEY = /^0x[0-9a-fA-F]{64}$/;
const NCT = /^NCT[0-9]{8}$/;
const CANDIDATE_VERSION = "trialproof/1.1.0";
const FINAL_ASSESSMENT_STATES = new Set([
  "DISCLOSURE_COMPLETE",
  "ACTION_REQUIRED",
  "REQUEST_MORE_INFO",
  "UNRESOLVED",
]);


function requireFinalized(receipt: SampleReceipt): void {
  if (!receipt.finalized || receipt.executionStatus !== "FINISHED_WITH_RETURN") {
    throw new Error("SAMPLE_FINALITY_OR_EXECUTION_FAILED");
  }
}

function validateCandidateManifest(manifest: DeploymentManifest): void {
  if (manifest.version !== CANDIDATE_VERSION) {
    throw new Error("SAMPLE_CANDIDATE_VERSION_MISMATCH");
  }
  if (
    !HASH.test(manifest.sourceSha256) ||
    !Number.isSafeInteger(manifest.sourceBytes) ||
    manifest.sourceBytes <= 0
  ) {
    throw new Error("SAMPLE_INVALID_SOURCE_IDENTITY");
  }
  if (
    !isSupportedNetwork(manifest.network, manifest.chainId) ||
    !ADDRESS.test(manifest.address)
  ) {
    throw new Error("SAMPLE_INVALID_MANIFEST");
  }
}

function parseReadback(
  value: string,
  nctId: string,
  expectedStates: ReadonlySet<string>,
): Record<string, unknown> {
  let assessment: Record<string, unknown>;
  try {
    assessment = JSON.parse(value) as Record<string, unknown>;
  } catch {
    throw new Error("SAMPLE_READBACK_MISMATCH");
  }
  if (
    assessment.nct_id !== nctId ||
    typeof assessment.assessment_id !== "string" ||
    typeof assessment.state !== "string" ||
    typeof assessment.certified !== "boolean"
  ) {
    throw new Error("SAMPLE_READBACK_MISMATCH");
  }
  if (!FINAL_ASSESSMENT_STATES.has(assessment.state as string) && assessment.state !== "REGISTERED") {
    throw new Error("SAMPLE_READBACK_STATE_INVALID");
  }
  if (!expectedStates.has(assessment.state as string)) {
    throw new Error("SAMPLE_READBACK_STATE_UNEXPECTED");
  }
  const resolution = assessment.resolution;
  const verdict =
    resolution && typeof resolution === "object"
      ? (resolution as Record<string, unknown>).verdict
      : undefined;
  if (
    assessment.certified !== (assessment.state === "DISCLOSURE_COMPLETE") ||
    (assessment.state === "REGISTERED"
      ? verdict !== undefined
      : verdict !== assessment.state)
  ) {
    throw new Error("SAMPLE_READBACK_MISMATCH");
  }
  return assessment;
}


export async function runSample(options: SampleOptions): Promise<SampleReport> {
  if ((options.mutationMode ?? "dry-run") !== "live") {
    throw new Error("SAMPLE_MUTATION_DISABLED");
  }
  const getEnv = options.getEnv ?? ((name: string) => process.env[name]);
  const privateKey = getEnv("GENLAYER_PRIVATE_KEY");
  if (!privateKey || !PRIVATE_KEY.test(privateKey)) {
    throw new Error("SAMPLE_INVALID_PRIVATE_KEY");
  }
  if (getEnv("TRIALPROOF_SAMPLE_CONFIRM") !== "RUN_TRIALPROOF_SAMPLE") {
    throw new Error("SAMPLE_CONFIRMATION_REQUIRED");
  }
  if (!NCT.test(options.nctId)) {
    throw new Error("SAMPLE_INVALID_NCT_ID");
  }
  validateCandidateManifest(options.manifest);
  const caller = await options.client.getCallerAddress(privateKey as `0x${string}`);
  if (!ADDRESS.test(caller)) {
    throw new Error("SAMPLE_INVALID_WALLET");
  }
  const registrationTransactionHash = await options.client.writeContract({
    address: options.manifest.address,
    args: [options.nctId],
    functionName: "register_study",
    privateKey: privateKey as `0x${string}`,
  });
  const registrationReceipt = await options.client.waitForReceipt(
    registrationTransactionHash,
  );
  requireFinalized(registrationReceipt);
  const registered = parseReadback(
    await options.client.readAssessmentByNctId(options.manifest.address, options.nctId),
    options.nctId,
    new Set(["REGISTERED"]),
  );
  const assessmentTransactionHash = await options.client.writeContract({
    address: options.manifest.address,
    args: [String(registered.assessment_id)],
    functionName: "assess",
    privateKey: privateKey as `0x${string}`,
  });
  const assessmentReceipt = await options.client.waitForReceipt(assessmentTransactionHash);
  requireFinalized(assessmentReceipt);
  const readback = parseReadback(
    await options.client.readAssessmentByNctId(options.manifest.address, options.nctId),
    options.nctId,
    FINAL_ASSESSMENT_STATES,
  );
  return {
    assessmentExecutionStatus: assessmentReceipt.executionStatus,
    assessmentFinalized: assessmentReceipt.finalized,
    assessmentTransactionHash,
    readback,
    registrationExecutionStatus: registrationReceipt.executionStatus,
    registrationFinalized: registrationReceipt.finalized,
    registrationTransactionHash,
  };
}


async function createLiveClient(
  privateKey: `0x${string}`,
  manifest: DeploymentManifest,
): Promise<SampleClient> {
  const [{ createAccount, createClient }, { studionet, testnetBradbury }, types] = await Promise.all([
    import("genlayer-js"),
    import("genlayer-js/chains"),
    import("genlayer-js/types"),
  ]);
  const account = createAccount(privateKey);
  const client = createClient({
    account,
    chain: manifest.network === "studionet" ? studionet : testnetBradbury,
  });
  return {
    getCallerAddress: async () => account.address,
    readAssessmentByNctId: async (address, nctId) =>
      String(
        await client.readContract({
          address: address as `0x${string}`,
          args: [nctId],
          functionName: "get_assessment_by_nct_id",
          jsonSafeReturn: true,
        }),
      ),
    waitForReceipt: async (hash) => {
      const receipt = await client.waitForTransactionReceipt({
        hash: hash as never,
        status: types.TransactionStatus.FINALIZED,
      });
      return {
        executionStatus: String(receipt.txExecutionResultName ?? ""),
        finalized:
          String(receipt.statusName) === String(types.TransactionStatus.FINALIZED) ||
          receipt.consensus_data?.final === true,
      };
    },
    writeContract: async ({ address, args, functionName }) =>
      client.writeContract({
        account,
        address: address as `0x${string}`,
        args,
        functionName,
        value: 0n,
      }),
  };
}


async function main(): Promise<void> {
  const live = process.argv.includes("--live");
  if (!live) {
    process.stdout.write(
      `${JSON.stringify({ action: "dry-run", mutationGuard: "set TRIALPROOF_SAMPLE_CONFIRM=RUN_TRIALPROOF_SAMPLE and pass --live", network: "testnet-bradbury" }, null, 2)}\n`,
    );
    return;
  }
  const manifestPath = process.argv.find((value) => value.endsWith(".json"));
  const nctId = process.argv.find((value) => /^NCT[0-9]{8}$/u.test(value));
  if (!manifestPath || !nctId) throw new Error("SAMPLE_ARGUMENTS_REQUIRED");
  const privateKey = process.env.GENLAYER_PRIVATE_KEY as `0x${string}` | undefined;
  if (!privateKey) throw new Error("SAMPLE_INVALID_PRIVATE_KEY");
  const manifest = JSON.parse(await readFile(manifestPath, "utf8")) as DeploymentManifest;
  const report = await runSample({
    client: await createLiveClient(privateKey, manifest),
    manifest,
    mutationMode: "live",
    nctId,
  });
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}


if (process.argv[1]?.endsWith("run-sample.ts") || process.argv[1]?.endsWith("run-sample.js")) {
  void main().catch((error: unknown) => {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  });
}
