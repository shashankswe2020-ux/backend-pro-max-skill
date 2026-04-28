import { spawn, ChildProcess } from "child_process";

/**
 * Minimal MCP stdio client — sends JSON-RPC requests to backendpro-mcp.
 * This is a thin wrapper; full MCP SDK usage is optional.
 */
export class McpClient {
  private proc: ChildProcess | undefined;
  private buffer = "";
  private reqId = 0;
  private pending = new Map<
    number,
    { resolve: (v: string) => void; reject: (e: Error) => void }
  >();

  constructor(private readonly command: string) {}

  async start(): Promise<void> {
    const [cmd, ...args] = this.command.split(/\s+/);
    this.proc = spawn(cmd, args, { stdio: ["pipe", "pipe", "pipe"] });

    this.proc.stdout?.on("data", (chunk: Buffer) => {
      this.buffer += chunk.toString();
      this.drain();
    });

    this.proc.on("error", (err) => {
      for (const p of this.pending.values()) {
        p.reject(err);
      }
      this.pending.clear();
    });
  }

  stop(): void {
    this.proc?.kill();
    this.proc = undefined;
  }

  async search(query: string, domain?: string): Promise<string> {
    const id = ++this.reqId;
    const params: Record<string, string> = { query };
    if (domain) {
      params.domain = domain;
    }

    const request = {
      jsonrpc: "2.0",
      id,
      method: "tools/call",
      params: {
        name: "search",
        arguments: params,
      },
    };

    return new Promise<string>((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      const msg = JSON.stringify(request);
      this.proc?.stdin?.write(msg + "\n");

      // Timeout after 10s
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error("MCP request timed out"));
        }
      }, 10_000);
    });
  }

  private drain(): void {
    const lines = this.buffer.split("\n");
    this.buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) {
        continue;
      }
      try {
        const msg = JSON.parse(line);
        if (msg.id && this.pending.has(msg.id)) {
          const p = this.pending.get(msg.id)!;
          this.pending.delete(msg.id);
          if (msg.error) {
            p.reject(new Error(msg.error.message ?? JSON.stringify(msg.error)));
          } else {
            const content = msg.result?.content?.[0]?.text ?? JSON.stringify(msg.result);
            p.resolve(content);
          }
        }
      } catch {
        // ignore malformed lines
      }
    }
  }
}
