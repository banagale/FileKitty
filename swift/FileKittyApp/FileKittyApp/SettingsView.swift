//
//  SettingsView.swift
//  FileKittyApp
//
//  Application settings and preferences
//

import SwiftUI

struct SettingsView: View {
    @Binding var settings: FileKittySettings
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Settings")
                    .font(.title2)
                    .fontWeight(.semibold)
                Spacer()
                Button("Done") {
                    dismiss()
                }
                .keyboardShortcut(.defaultAction)
            }
            .padding()

            Divider()

            // Settings form
            Form {
                Section("Output Options") {
                    Toggle("Include File Tree", isOn: $settings.includeTree)
                        .help("Include a visual tree of the project structure")

                    Toggle("Include Last Modified Dates", isOn: $settings.includeDateModified)
                        .help("Show last modified timestamp for each file")

                    Toggle("Auto-copy to Clipboard", isOn: $settings.autoCopy)
                        .help("Automatically copy output to clipboard when generated")
                }

                Section("File Tree Settings") {
                    TextField("Base Directory", text: $settings.treeBaseDir)
                        .help("Base directory for tree generation (empty for auto-detect)")

                    TextField("Ignore Pattern (Regex)", text: $settings.treeIgnoreRegex)
                        .help("Regex pattern for files/folders to ignore")
                        .font(.system(.body, design: .monospaced))
                }

                Section("Advanced") {
                    HStack {
                        Text("Python Path")
                        Spacer()
                        Text(CLIInterface.findPython())
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    Button("Reset to Defaults") {
                        settings = FileKittySettings()
                    }
                }
            }
            .formStyle(.grouped)
            .padding()
        }
        .frame(width: 500, height: 600)
    }
}

#Preview {
    SettingsView(settings: .constant(FileKittySettings()))
}
