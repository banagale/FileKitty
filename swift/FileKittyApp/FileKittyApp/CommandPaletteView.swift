//
//  CommandPaletteView.swift
//  FileKittyApp
//
//  Command palette for quick actions (⌘K)
//

import SwiftUI

struct CommandPaletteView: View {
    @ObservedObject var viewModel: FileKittyViewModel
    @Binding var isPresented: Bool
    @State private var searchText = ""
    @State private var selectedIndex = 0

    var body: some View {
        VStack(spacing: 0) {
            // Search field
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.secondary)

                TextField("Search commands...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.title3)
                    .onSubmit {
                        executeSelectedCommand()
                    }

                if !searchText.isEmpty {
                    Button(action: { searchText = "" }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.secondary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding()
            .background(Color(NSColor.textBackgroundColor))

            Divider()

            // Command list
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    ForEach(Array(filteredCommands.enumerated()), id: \.offset) { index, command in
                        CommandRowView(command: command, isSelected: index == selectedIndex)
                            .contentShape(Rectangle())
                            .onTapGesture {
                                executeCommand(command)
                            }
                            .background(index == selectedIndex ? Color.accentColor.opacity(0.2) : Color.clear)
                    }
                }
            }
            .frame(maxHeight: 400)
        }
        .frame(width: 600)
        .background(Color(NSColor.windowBackgroundColor))
        .cornerRadius(12)
        .shadow(radius: 20)
        .onAppear {
            selectedIndex = 0
        }
        .onKeyPress(.upArrow) {
            selectedIndex = max(0, selectedIndex - 1)
            return .handled
        }
        .onKeyPress(.downArrow) {
            selectedIndex = min(filteredCommands.count - 1, selectedIndex + 1)
            return .handled
        }
        .onKeyPress(.return) {
            executeSelectedCommand()
            return .handled
        }
        .onKeyPress(.escape) {
            isPresented = false
            return .handled
        }
    }

    private var filteredCommands: [Command] {
        if searchText.isEmpty {
            return allCommands
        }

        return allCommands.filter { command in
            command.title.localizedCaseInsensitiveContains(searchText) ||
                command.description.localizedCaseInsensitiveContains(searchText)
        }
    }

    private var allCommands: [Command] {
        [
            Command(
                title: "Open Files",
                description: "Add files to current session",
                icon: "doc.badge.plus",
                action: { viewModel.openFiles() }
            ),
            Command(
                title: "New Session",
                description: "Start a new session",
                icon: "plus.square",
                action: { viewModel.createNewSession() }
            ),
            Command(
                title: "Load Session",
                description: "Load a session from file",
                icon: "folder",
                action: { viewModel.loadSessionFromFile() }
            ),
            Command(
                title: "Copy to Clipboard",
                description: "Copy output to clipboard",
                icon: "doc.on.clipboard",
                action: { viewModel.copyToClipboard() }
            ),
            Command(
                title: "Export Session",
                description: "Export current session to file",
                icon: "square.and.arrow.up",
                action: {
                    if let session = viewModel.currentSession {
                        viewModel.exportSession(session)
                    }
                }
            ),
            Command(
                title: "Share Session",
                description: "Share current session",
                icon: "square.and.arrow.up.on.square",
                action: {
                    if let session = viewModel.currentSession {
                        viewModel.shareSession(session)
                    }
                }
            ),
            Command(
                title: "Refresh Output",
                description: "Regenerate output with current selection",
                icon: "arrow.clockwise",
                action: {
                    Task {
                        if let session = viewModel.currentSession {
                            _ = try? await viewModel.cliInterface.updateSelection(
                                sessionId: session.id,
                                selectionState: session.selectionState
                            )
                        }
                    }
                }
            ),
            Command(
                title: "Clear Selection",
                description: "Clear all file and symbol selections",
                icon: "clear",
                action: {
                    viewModel.selectedFiles = []
                    if var session = viewModel.currentSession {
                        session.selectionState = SelectionState()
                        viewModel.currentSession = session
                    }
                }
            ),
            Command(
                title: "Settings",
                description: "Open application settings",
                icon: "gear",
                action: {
                    // Handled by parent view
                }
            ),
        ]
    }

    private func executeSelectedCommand() {
        guard selectedIndex < filteredCommands.count else { return }
        executeCommand(filteredCommands[selectedIndex])
    }

    private func executeCommand(_ command: Command) {
        isPresented = false
        command.action()
    }
}

struct CommandRowView: View {
    let command: Command
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: command.icon)
                .font(.title3)
                .foregroundColor(.accentColor)
                .frame(width: 24, height: 24)

            VStack(alignment: .leading, spacing: 2) {
                Text(command.title)
                    .font(.body)

                Text(command.description)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
    }
}

struct Command {
    let title: String
    let description: String
    let icon: String
    let action: () -> Void
}

#Preview {
    CommandPaletteView(
        viewModel: FileKittyViewModel(),
        isPresented: .constant(true)
    )
}
