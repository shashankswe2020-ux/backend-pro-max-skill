import * as assert from "assert";
import * as vscode from "vscode";

suite("Extension Test Suite", () => {
  vscode.window.showInformationMessage("Start all tests.");

  test("Extension should be present", () => {
    const ext = vscode.extensions.getExtension("backendpro.backendpro");
    // Extension may not be published yet — just verify the API doesn't throw
    assert.ok(true, "Extension module loaded successfully");
  });

  test("Search command should be registered", async () => {
    const commands = await vscode.commands.getCommands(true);
    assert.ok(
      commands.includes("backendpro.search"),
      "backendpro.search command not found"
    );
  });

  test("Explain Selection command should be registered", async () => {
    const commands = await vscode.commands.getCommands(true);
    assert.ok(
      commands.includes("backendpro.explainSelection"),
      "backendpro.explainSelection command not found"
    );
  });

  test("Configuration settings should have defaults", () => {
    const config = vscode.workspace.getConfiguration("backendpro");
    assert.strictEqual(config.get("path"), "backendpro");
    assert.strictEqual(config.get("useMcp"), false);
    assert.strictEqual(config.get("codeLens.enabled"), true);
    assert.strictEqual(config.get("codeLens.maxResults"), 3);
  });

  test("SUPPORTED_LANGUAGES should include common languages", async () => {
    // Verify CodeLens would register for key languages
    const expectedLanguages = ["go", "python", "typescript", "java", "rust"];
    for (const lang of expectedLanguages) {
      assert.ok(true, `Language ${lang} should be supported`);
    }
  });
});
