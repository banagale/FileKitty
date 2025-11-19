//
//  MenuBarManager.swift
//  FileKittyApp
//
//  Menu bar app mode for quick access
//

import SwiftUI
import AppKit

class MenuBarManager: ObservableObject {
    @Published var isMenuBarMode = false
    private var statusItem: NSStatusItem?
    private var popover: NSPopover?

    func enableMenuBarMode() {
        guard statusItem == nil else { return }

        // Create status item
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)

        if let button = statusItem?.button {
            button.image = NSImage(systemSymbolName: "cat", accessibilityDescription: "FileKitty")
            button.action = #selector(togglePopover)
            button.target = self
        }

        // Create popover
        popover = NSPopover()
        popover?.contentSize = NSSize(width: 400, height: 600)
        popover?.behavior = .transient
        popover?.contentViewController = NSHostingController(rootView: MenuBarContentView())

        isMenuBarMode = true

        // Hide main window
        NSApp.windows.first?.orderOut(nil)
    }

    func disableMenuBarMode() {
        statusItem = nil
        popover = nil
        isMenuBarMode = false

        // Show main window
        NSApp.windows.first?.makeKeyAndOrderFront(nil)
    }

    @objc private func togglePopover() {
        guard let button = statusItem?.button, let popover = popover else { return }

        if popover.isShown {
            popover.performClose(nil)
        } else {
            popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
        }
    }
}

// MARK: - Menu Bar Content View

struct MenuBarContentView: View {
    @StateObject private var viewModel = FileKittyViewModel()
    @State private var selectedFiles: [URL] = []

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Image(systemName: "cat.fill")
                    .font(.title2)
                    .foregroundColor(.accentColor)

                Text("FileKitty")
                    .font(.title2)
                    .fontWeight(.semibold)

                Spacer()

                Button(action: { NSApp.windows.first?.makeKeyAndOrderFront(nil) }) {
                    Image(systemName: "arrow.up.right.square")
                }
                .buttonStyle(.plain)
                .help("Open main window")
            }
            .padding()

            Divider()

            // Quick actions
            ScrollView {
                VStack(spacing: 12) {
                    QuickActionButton(
                        title: "Process Files",
                        icon: "doc.badge.plus",
                        color: .blue
                    ) {
                        viewModel.openFiles()
                    }

                    QuickActionButton(
                        title: "Load Session",
                        icon: "folder",
                        color: .green
                    ) {
                        viewModel.loadSessionFromFile()
                    }

                    QuickActionButton(
                        title: "New Session",
                        icon: "plus.square",
                        color: .orange
                    ) {
                        viewModel.createNewSession()
                    }

                    if let session = viewModel.currentSession {
                        Divider()
                            .padding(.vertical, 8)

                        VStack(alignment: .leading, spacing: 8) {
                            Text("Current Session")
                                .font(.caption)
                                .foregroundColor(.secondary)

                            HStack {
                                VStack(alignment: .leading) {
                                    Text("\(session.files.count) files")
                                        .font(.body)

                                    if let projectRoot = session.projectRoot {
                                        Text(URL(fileURLWithPath: projectRoot).lastPathComponent)
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                }

                                Spacer()

                                Button(action: { viewModel.copyToClipboard() }) {
                                    Image(systemName: "doc.on.clipboard")
                                }
                                .buttonStyle(.borderless)
                            }
                            .padding()
                            .background(Color.secondary.opacity(0.1))
                            .cornerRadius(8)
                        }
                    }

                    Divider()
                        .padding(.vertical, 8)

                    // Recent sessions
                    if !viewModel.sessionHistory.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Recent Sessions")
                                .font(.caption)
                                .foregroundColor(.secondary)

                            ForEach(viewModel.sessionHistory.prefix(5)) { session in
                                SessionQuickView(session: session) {
                                    viewModel.loadSession(session)
                                }
                            }
                        }
                    }
                }
                .padding()
            }
        }
        .frame(width: 400, height: 600)
        .onAppear {
            viewModel.loadHistory()
        }
    }
}

struct QuickActionButton: View {
    let title: String
    let icon: String
    let color: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Image(systemName: icon)
                    .font(.title3)
                    .foregroundColor(color)
                    .frame(width: 32)

                Text(title)
                    .font(.body)

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding()
            .background(Color.secondary.opacity(0.1))
            .cornerRadius(8)
        }
        .buttonStyle(.plain)
    }
}

struct SessionQuickView: View {
    let session: PromptSession
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    if let projectRoot = session.projectRoot {
                        Text(URL(fileURLWithPath: projectRoot).lastPathComponent)
                            .font(.caption)
                            .lineLimit(1)
                    }

                    Text("\(session.files.count) files")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }

                Spacer()

                Text(relativeTime(session.timestamp))
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            .padding(.vertical, 4)
        }
        .buttonStyle(.plain)
    }

    private func relativeTime(_ date: Date) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: date, relativeTo: Date())
    }
}
