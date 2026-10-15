import type { ProcessScenario } from "../../domain/process/processScenario.js";
import { providerHostEnvironment } from "../providerProcessEnvironment.js";

interface ProcessCaptureEnvironmentOptions {
  readonly scenario: ProcessScenario;
  readonly runId: string;
  readonly hostEnvironment: Readonly<Record<string, string | undefined>>;
}

/** Inherit runtime coordinates, then preserve explicit scenario overrides. */
export const makeProcessCaptureEnvironment = (
  options: ProcessCaptureEnvironmentOptions,
): Record<string, string> => ({
  ...providerHostEnvironment(options.hostEnvironment),
  ...options.scenario.environment,
  TERM:
    options.scenario.environment.TERM ??
    options.hostEnvironment.TERM ??
    "xterm-256color",
  REA_PROCESS_RUN_ID: options.runId,
});
