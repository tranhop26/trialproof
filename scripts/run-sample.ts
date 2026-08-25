import { readFile } from "node:fs/promises";

import type { DeploymentManifest } from "./write-manifest.js";


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
const PRIVATE_KEY = /^0x[0-9a-fA-F]{64}$/;
const NCT = /^NCT[0-9]{8}$/;


function requireFinalized(receipt: SampleReceipt): void {
  if (!receipt.finalized || receipt.executionStatus !== "FINISHED_WITH_RETURN") {
    throw new Error("SAMPLE_FINALITY_OR_EXECUTION_FAILED");
  }
}

function parseReadback(value: string, nctId: string): Record<string, unknown> {
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
  if (
    options.manifest.chainId !== 4221 ||
    options.manifest.network !== "testnet-bradbury" ||
    !ADDRESS.test(options.manifest.address)
  ) {
    throw new Error("SAMPLE_INVALID_MANIFEST");
  }
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


async function createLiveClient(privateKey: `0x${string}`): Promise<SampleClient> {
  const [{ createAccount, createClient }, { testnetBradbury }, types] = await Promise.all([
    import("genlayer-js"),
    import("genlayer-js/chains"),
    import("genlayer-js/types"),
  ]);
  const account = createAccount(privateKey);
  const client = createClient({ account, chain: testnetBradbury });
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
    client: await createLiveClient(privateKey),
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
