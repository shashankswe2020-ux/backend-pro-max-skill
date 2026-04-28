package com.backendpro.intellij;

import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.ui.Messages;
import org.jetbrains.annotations.NotNull;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.stream.Collectors;

/**
 * Tools → Backend Pro Max → Search Knowledge Base
 * Shells out to `backendpro --json` and displays results.
 */
public class SearchAction extends AnAction {

    @Override
    public void actionPerformed(@NotNull AnActionEvent e) {
        String query = Messages.showInputDialog(
                e.getProject(),
                "Search Backend Pro Max:",
                "Backend Pro Max: Search",
                null
        );
        if (query == null || query.isBlank()) {
            return;
        }

        try {
            ProcessBuilder pb = new ProcessBuilder("backendpro", query, "--json");
            pb.redirectErrorStream(true);
            Process proc = pb.start();
            String output = new BufferedReader(new InputStreamReader(proc.getInputStream()))
                    .lines().collect(Collectors.joining("\n"));
            proc.waitFor();
            Messages.showInfoMessage(e.getProject(), output, "Backend Pro Max Results");
        } catch (Exception ex) {
            Messages.showErrorDialog(e.getProject(),
                    "Error running backendpro: " + ex.getMessage(),
                    "Backend Pro Max Error");
        }
    }
}
