package com.backendpro.intellij;

import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.actionSystem.CommonDataKeys;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.ui.Messages;
import org.jetbrains.annotations.NotNull;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.stream.Collectors;

/**
 * Tools → Backend Pro Max → Explain Selection
 * Takes editor selection, searches BPM, shows results.
 */
public class ExplainSelectionAction extends AnAction {

    @Override
    public void actionPerformed(@NotNull AnActionEvent e) {
        Editor editor = e.getData(CommonDataKeys.EDITOR);
        if (editor == null) {
            return;
        }
        String selected = editor.getSelectionModel().getSelectedText();
        if (selected == null || selected.isBlank()) {
            Messages.showWarningDialog(e.getProject(), "No text selected.", "Backend Pro Max");
            return;
        }

        try {
            ProcessBuilder pb = new ProcessBuilder("backendpro", selected.trim(), "--json");
            pb.redirectErrorStream(true);
            Process proc = pb.start();
            String output = new BufferedReader(new InputStreamReader(proc.getInputStream()))
                    .lines().collect(Collectors.joining("\n"));
            proc.waitFor();
            Messages.showInfoMessage(e.getProject(), output, "Backend Pro Max: " + selected.trim());
        } catch (Exception ex) {
            Messages.showErrorDialog(e.getProject(),
                    "Error running backendpro: " + ex.getMessage(),
                    "Backend Pro Max Error");
        }
    }

    @Override
    public void update(@NotNull AnActionEvent e) {
        Editor editor = e.getData(CommonDataKeys.EDITOR);
        e.getPresentation().setEnabled(
                editor != null && editor.getSelectionModel().hasSelection()
        );
    }
}
