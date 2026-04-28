import * as vscode from "vscode";
import { runCliSearch } from "./cli";
import { BackendProCodeLensProvider, SUPPORTED_LANGUAGES } from "./codelens";
import { McpClient } from "./mcp-client";

let mcpClient: McpClient | undefined;

export function activate(context: vscode.ExtensionContext): void {
  const outputChannel = vscode.window.createOutputChannel("Backend Pro Max");

  // ── Search command ─────────────────────────────────────────────────
  const searchCmd = vscode.commands.registerCommand(
    "backendpro.search",
    async () => {
      const query = await vscode.window.showInputBox({
        prompt: "Search Backend Pro Max knowledge base",
        placeHolder: "e.g. circuit breaker, kafka vs rabbitmq, idempotency",
      });
      if (!query) {
        return;
      }
      await executeSearch(query, outputChannel);
    }
  );

  // ── Explain Selection command ──────────────────────────────────────
  const explainCmd = vscode.commands.registerCommand(
    "backendpro.explainSelection",
    async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage("No active editor.");
        return;
      }
      const selection = editor.document.getText(editor.selection);
      if (!selection.trim()) {
        vscode.window.showWarningMessage("No text selected.");
        return;
      }
      await executeSearch(selection.trim(), outputChannel);
    }
  );

  // ── CodeLens provider ─────────────────────────────────────────────
  const config = vscode.workspace.getConfiguration("backendpro");
  if (config.get<boolean>("codeLens.enabled", true)) {
    const codeLensProvider = new BackendProCodeLensProvider();
    for (const lang of SUPPORTED_LANGUAGES) {
      context.subscriptions.push(
        vscode.languages.registerCodeLensProvider({ language: lang }, codeLensProvider)
      );
    }
  }

  context.subscriptions.push(searchCmd, explainCmd, outputChannel);
}

async function executeSearch(
  query: string,
  outputChannel: vscode.OutputChannel
): Promise<void> {
  const config = vscode.workspace.getConfiguration("backendpro");
  const useMcp = config.get<boolean>("useMcp", false);
  const domain = config.get<string>("defaultDomain", "") || undefined;

  outputChannel.clear();
  outputChannel.show(true);
  outputChannel.appendLine(`🔍 Searching: ${query}\n`);

  try {
    let result: string;
    if (useMcp) {
      result = await searchViaMcp(query, domain, config);
    } else {
      result = await searchViaCli(query, domain, config);
    }
    outputChannel.appendLine(result);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    outputChannel.appendLine(`❌ Error: ${msg}`);
    vscode.window.showErrorMessage(`Backend Pro Max: ${msg}`);
  }
}

async function searchViaCli(
  query: string,
  domain: string | undefined,
  config: vscode.WorkspaceConfiguration
): Promise<string> {
  const cliPath = config.get<string>("path", "backendpro");
  const args = [query];
  if (domain) {
    args.push("--domain", domain);
  }
  return runCliSearch(cliPath, args);
}

async function searchViaMcp(
  query: string,
  domain: string | undefined,
  config: vscode.WorkspaceConfiguration
): Promise<string> {
  if (!mcpClient) {
    const cmd = config.get<string>("mcpCommand", "backendpro-mcp");
    mcpClient = new McpClient(cmd);
    await mcpClient.start();
  }
  return mcpClient.search(query, domain);
}

export function deactivate(): void {
  if (mcpClient) {
    mcpClient.stop();
    mcpClient = undefined;
  }
}
