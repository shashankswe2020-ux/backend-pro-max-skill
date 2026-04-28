import * as vscode from "vscode";
import { runCliSearch } from "./cli";

/** Map file language ID → backendpro stack name. */
const LANG_TO_STACK: Record<string, string> = {
  go: "go",
  java: "java-spring",
  python: "python-fastapi",
  typescript: "nodejs-express",
  javascript: "nodejs-express",
  rust: "rust-axum",
  csharp: "csharp-aspnet",
  kotlin: "kotlin-spring",
  scala: "scala-akka",
  elixir: "elixir-phoenix",
  ruby: "ruby-rails",
  php: "php-laravel",
  cpp: "cpp",
};

export const SUPPORTED_LANGUAGES = Object.keys(LANG_TO_STACK);

export class BackendProCodeLensProvider implements vscode.CodeLensProvider {
  private _onDidChange = new vscode.EventEmitter<void>();
  public readonly onDidChangeCodeLenses = this._onDidChange.event;

  async provideCodeLenses(
    document: vscode.TextDocument,
    _token: vscode.CancellationToken
  ): Promise<vscode.CodeLens[]> {
    const config = vscode.workspace.getConfiguration("backendpro");
    if (!config.get<boolean>("codeLens.enabled", true)) {
      return [];
    }

    const langId = document.languageId;
    const stack = LANG_TO_STACK[langId];
    if (!stack) {
      return [];
    }

    const maxResults = config.get<number>("codeLens.maxResults", 3);
    const cliPath = config.get<string>("path", "backendpro");

    try {
      const raw = await runCliSearch(cliPath, [
        "best practices",
        "--stack",
        stack,
        "--json",
        "-n",
        String(maxResults),
      ]);
      const result = JSON.parse(raw);
      const rows: Array<{ Guideline?: string; Category?: string }> =
        result.results ?? [];

      const topLine = new vscode.Range(0, 0, 0, 0);
      return rows.map((row) => {
        const title = row.Guideline ?? row.Category ?? "Stack guideline";
        return new vscode.CodeLens(topLine, {
          title: `📘 BPM: ${title}`,
          command: "backendpro.search",
          arguments: [],
          tooltip: `Backend Pro Max — ${stack} guideline`,
        });
      });
    } catch {
      return [];
    }
  }
}
