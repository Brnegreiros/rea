import type { FridaScriptSource } from "../application/frida/FridaInstrumentationPort.js";
import {
  RegularFileCleanupFailure,
  withRegularFile,
} from "../application/RegularFileRead.js";
import type { ArtifactResourceScope } from "../artifacts/ArtifactResourceScope.js";
import {
  AnalysisInputError,
  AnalysisAccessDeniedError,
  AnalysisCancelledError,
  AnalysisCapabilityUnavailableError,
} from "../domain/analysisErrorCore.js";
import type { AnalysisError } from "../domain/analysisErrorBase.js";
import { ArtifactReaderFailure } from "../artifacts/ArtifactReader.js";
import { RegularFileChangedError } from "../filesystem/RegularFile.js";
import { readBoundedFileBytes } from "../process/BoundedFileBytes.js";

// Per-script acquisition budget, not a Frida format limit. Keep source buffers
// and UTF-16 decoding bounded separately from the 16 MiB message capture budget.
export const MAX_FRIDA_SCRIPT_BYTES = 4 * 1024 * 1024;

const sourceTooLarge = (source: FridaScriptSource) =>
  new AnalysisInputError("load_frida_script", undefined, [
    {
      path: [source.sourceKind === "file" ? "path" : "source"],
      reason: "invalid_value",
      message: `Frida script source exceeds the ${MAX_FRIDA_SCRIPT_BYTES} byte acquisition limit.`,
    },
  ]);

/** Read one stable regular file, or admit inline text, before native effects. */
export const readFridaScriptSource = (
  source: FridaScriptSource,
  resources: ArtifactResourceScope,
  signal?: AbortSignal,
): Promise<string> => {
  if (source.sourceKind === "inline")
    return resources.run(async () => {
      signal?.throwIfAborted();
      if (Buffer.byteLength(source.source, "utf8") > MAX_FRIDA_SCRIPT_BYTES)
        throw sourceTooLarge(source);
      return source.source;
    });
  return withRegularFile(
    source.path,
    async (handle, stats) => {
      if (stats.size > MAX_FRIDA_SCRIPT_BYTES) throw sourceTooLarge(source);
      // Read through EOF with a ceiling: the initial stat is not authority to
      // allocate an unbounded buffer if the file grows while it is being read.
      const bytes = await readBoundedFileBytes(
        handle,
        MAX_FRIDA_SCRIPT_BYTES,
        signal,
      );
      if (bytes === undefined) throw sourceTooLarge(source);
      if (bytes.length !== stats.size)
        throw new RegularFileChangedError(source.path);
      // Preserve the previous readFile(path, "utf8") decoding, including BOM.
      const text = bytes.toString("utf8");
      // Invalid UTF-8 retains readFile's replacement semantics, but expansion
      // must not bypass the same UTF-8 budget enforced for inline input.
      if (Buffer.byteLength(text, "utf8") > MAX_FRIDA_SCRIPT_BYTES)
        throw sourceTooLarge(source);
      return text;
    },
    { signal, resources },
  );
};

/** Project acquisition and retained-cleanup failures at their owning boundary. */
export const fridaScriptSourceError = (
  source: FridaScriptSource,
  cause: unknown,
  signal?: AbortSignal,
): AnalysisError => {
  const cleanup =
    cause instanceof RegularFileCleanupFailure
      ? {
          reason: String(
            cause.cleanupCause instanceof Error
              ? cause.cleanupCause.message
              : cause.cleanupCause,
          ),
          resources: [cause.path],
        }
      : cause instanceof ArtifactReaderFailure
        ? cause.cleanup
        : undefined;
  if (signal?.aborted)
    return new AnalysisCancelledError("load_frida_script", {
      cause: signal.reason,
      ...(cleanup === undefined ? {} : { cleanup }),
    });
  if (cleanup !== undefined)
    return new AnalysisCapabilityUnavailableError(
      "frida",
      "load_frida_script",
      "Frida script source cleanup remains incomplete.",
      { cause, cleanup },
    );
  if (cause instanceof AnalysisInputError) return cause;
  const sourcePath = source.sourceKind === "file" ? source.path : undefined;
  return cause instanceof Error &&
    "code" in cause &&
    (cause.code === "EACCES" || cause.code === "EPERM")
    ? new AnalysisAccessDeniedError(
        "load_frida_script",
        sourcePath ?? "<inline>",
        cause.code,
        { cause },
      )
    : new AnalysisInputError("load_frida_script", { cause }, [
        {
          path: ["path"],
          reason: "invalid_value",
          message: `Cannot read Frida script file ${sourcePath ?? "<inline>"}.`,
        },
      ]);
};
