// Curated synthetic inputs only. No devices, credentials or external targets.
import fs from "node:fs";
import net from "node:net";
import { Worker } from "node:worker_threads";

const mode = process.argv[2];
if (mode === "basic") {
  console.log(
    JSON.stringify({
      explicit: process.env.SYNTHETIC_VALUE,
      empty: process.env.EMPTY === "",
      absent: process.env.ABSENT === undefined,
      ambient: process.env.UNRELATED_AMBIENT === undefined,
      owned: typeof process.env.REA_PROCESS_RUN_ID === "string",
    }),
  );
  fs.writeFileSync("/work/child-marker", "synthetic");
} else if (mode === "echo") {
  process.stdin.once("data", (data) => {
    process.stdout.write(data);
    process.exitCode = 0;
  });
} else if (mode === "wait") {
  setInterval(() => {}, 100);
} else if (mode === "error") {
  throw new Error("SYNTHETIC_DIAGNOSTIC_CANARY");
} else if (mode === "probe") {
  const denied = [];
  for (const path of [
    "/run/rea-controller.sock",
    "/var/lib/rea-controller/state.db",
    "/home/ubuntu/.bashrc",
  ]) {
    try {
      fs.readFileSync(path);
      denied.push(false);
    } catch {
      denied.push(true);
    }
  }
  let writeDenied = false;
  try {
    fs.writeFileSync("/app/namespace-write-marker", "synthetic");
  } catch {
    writeDenied = true;
  }
  let importWriteDenied = false;
  try {
    fs.writeFileSync(
      "/app/node_modules/namespace-import-marker.cjs",
      "synthetic",
    );
  } catch {
    importWriteDenied = true;
  }
  const socket = net.connect({ host: "1.1.1.1", port: 443 });
  socket.once("error", () =>
    console.log(
      JSON.stringify({
        denied,
        writeDenied,
        importWriteDenied,
        networkDenied: true,
      }),
    ),
  );
  socket.setTimeout(500, () => {
    socket.destroy();
    console.log("network-probe-timeout");
  });
} else if (mode === "disk") {
  try {
    const fd = fs.openSync("/work/bounded-disk", "w");
    const block = Buffer.alloc(1024 * 1024, 1);
    for (let index = 0; index < 20; index++) fs.writeSync(fd, block);
    fs.closeSync(fd);
  } catch (error) {
    console.log(
      JSON.stringify({
        diskDenied: error.code === "ENOSPC" || error.code === "EFBIG",
      }),
    );
  }
} else if (mode === "cpu") {
  const workers = Array.from(
    { length: 3 },
    () => new Worker("while(true){}", { eval: true }),
  );
  setTimeout(async () => {
    await Promise.all(workers.map((worker) => worker.terminate()));
    console.log("bounded-cpu-done");
  }, 500);
} else {
  throw new Error("unsupported synthetic fixture");
}
