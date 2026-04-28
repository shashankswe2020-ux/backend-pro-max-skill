import { execFile } from "child_process";

/**
 * Run `backendpro` CLI and return stdout.
 */
export function runCliSearch(
  cliPath: string,
  args: string[]
): Promise<string> {
  return new Promise((resolve, reject) => {
    execFile(cliPath, args, { timeout: 15_000 }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error(stderr || error.message));
        return;
      }
      resolve(stdout);
    });
  });
}
