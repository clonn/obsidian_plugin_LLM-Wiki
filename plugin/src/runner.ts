import { spawn } from "child_process";

export interface RunOptions {
  cmd: string;
  args: string[];
  cwd: string;
  onStdout?: (chunk: string) => void;
  onStderr?: (chunk: string) => void;
}

/** Promise wrapper around `child_process.spawn` with streamed callbacks. */
export function runStreaming(opts: RunOptions): Promise<number> {
  return new Promise((resolve, reject) => {
    const child = spawn(opts.cmd, opts.args, {
      cwd: opts.cwd,
      shell: false,
      env: { ...process.env },
    });
    child.stdout.setEncoding("utf-8");
    child.stderr.setEncoding("utf-8");
    child.stdout.on("data", (chunk: string) => opts.onStdout?.(chunk));
    child.stderr.on("data", (chunk: string) => opts.onStderr?.(chunk));
    child.on("error", reject);
    child.on("close", (code) => resolve(code ?? 0));
  });
}
