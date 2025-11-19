//
//  ContentView.swift
//  FileKittyApp
//
//  Main application view with split layout and drag-and-drop
//

import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @StateObject private var viewModel = FileKittyViewModel()
    @State private var showingCommandPalette = false
    @State private var showingSettings = false

    var body: some View {
        NavigationSplitView {
            // Sidebar with history
            SidebarView(viewModel: viewModel)
                .frame(minWidth: 200, idealWidth: 250)
        } detail: {
            // Main content area
            MainContentView(
                viewModel: viewModel,
                showingCommandPalette: $showingCommandPalette,
                showingSettings: $showingSettings
            )
        }
        .sheet(isPresented: $showingCommandPalette) {
            CommandPaletteView(viewModel: viewModel, isPresented: $showingCommandPalette)
        }
        .sheet(isPresented: $showingSettings) {
            SettingsView(settings: $viewModel.settings)
        }
        .onAppear {
            viewModel.loadHistory()
        }
    }
}

// MARK: - Sidebar View

struct SidebarView: View {
    @ObservedObject var viewModel: FileKittyViewModel

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Sessions")
                    .font(.headline)
                Spacer()
                Button(action: { viewModel.createNewSession() }) {
                    Image(systemName: "plus")
                }
                .buttonStyle(.borderless)
            }
            .padding()

            Divider()

            // Session list
            List(selection: $viewModel.selectedSessionId) {
                ForEach(viewModel.sessionHistory) { session in
                    SessionRowView(session: session)
                        .tag(session.id)
                        .contextMenu {
                            Button("Open") {
                                viewModel.loadSession(session)
                            }
                            Button("Duplicate") {
                                viewModel.duplicateSession(session)
                            }
                            Divider()
                            Button("Export...") {
                                viewModel.exportSession(session)
                            }
                            Button("Share...") {
                                viewModel.shareSession(session)
                            }
                            Divider()
                            Button("Delete", role: .destructive) {
                                viewModel.deleteSession(session)
                            }
                        }
                }
            }
            .listStyle(.sidebar)
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Menu {
                    Button("New Session") {
                        viewModel.createNewSession()
                    }
                    Button("Open Files...") {
                        viewModel.openFiles()
                    }
                    Button("Load Session...") {
                        viewModel.loadSessionFromFile()
                    }
                    Divider()
                    Button("Settings...") {
                        // Show settings
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
            }
        }
    }
}

struct SessionRowView: View {
    let session: PromptSession

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(sessionTitle)
                .font(.body)
            Text(sessionSubtitle)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(.vertical, 4)
    }

    private var sessionTitle: String {
        if let projectRoot = session.projectRoot {
            return URL(fileURLWithPath: projectRoot).lastPathComponent
        }
        return "Session \(session.id.prefix(8))"
    }

    private var sessionSubtitle: String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .short
        let timeAgo = formatter.localizedString(for: session.timestamp, relativeTo: Date())
        return "\(session.files.count) files • \(timeAgo)"
    }
}

// MARK: - Main Content View

struct MainContentView: View {
    @ObservedObject var viewModel: FileKittyViewModel
    @Binding var showingCommandPalette: Bool
    @Binding var showingSettings: Bool

    var body: some View {
        HSplitView {
            // Left: File list and selection
            FileListView(viewModel: viewModel)
                .frame(minWidth: 300, idealWidth: 400)

            // Right: Output preview
            OutputPreviewView(viewModel: viewModel)
                .frame(minWidth: 400, idealWidth: 600)
        }
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Button(action: { viewModel.copyToClipboard() }) {
                    Label("Copy", systemImage: "doc.on.clipboard")
                }
                .disabled(viewModel.currentSession?.outputText == nil)

                Button(action: { showingSettings = true }) {
                    Label("Settings", systemImage: "gear")
                }

                Button(action: { showingCommandPalette = true }) {
                    Label("Command Palette", systemImage: "command")
                }
                .keyboardShortcut("k", modifiers: .command)
            }
        }
    }
}

// MARK: - File List View

struct FileListView: View {
    @ObservedObject var viewModel: FileKittyViewModel
    @State private var isDragOver = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Files")
                    .font(.headline)
                Spacer()
                Button(action: { viewModel.openFiles() }) {
                    Image(systemName: "plus")
                }
                .buttonStyle(.borderless)
            }
            .padding()

            Divider()

            // File list
            if let session = viewModel.currentSession {
                List(selection: $viewModel.selectedFiles) {
                    ForEach(session.fileMetadata) { metadata in
                        FileRowView(metadata: metadata, viewModel: viewModel)
                            .tag(metadata.id)
                    }
                    .onDelete { indexSet in
                        viewModel.removeFiles(at: indexSet)
                    }
                }
                .listStyle(.inset)
            } else {
                // Empty state with drag-and-drop
                DropZoneView(isDragOver: $isDragOver) {
                    viewModel.handleDrop($0)
                }
            }
        }
        .onDrop(of: [.fileURL], isTargeted: $isDragOver) { providers in
            return viewModel.handleDrop(providers)
        }
        .overlay(
            isDragOver ? DragOverlayView() : nil
        )
    }
}

struct FileRowView: View {
    let metadata: FileMetadata
    @ObservedObject var viewModel: FileKittyViewModel
    @State private var isExpanded = false

    var body: some View {
        DisclosureGroup(isExpanded: $isExpanded) {
            if metadata.language == "python", let symbols = viewModel.fileSymbols[metadata.path] {
                SymbolListView(
                    symbols: symbols,
                    selectedItems: binding(for: metadata.path)
                )
            }
        } label: {
            HStack {
                Image(systemName: iconName)
                    .foregroundColor(iconColor)

                VStack(alignment: .leading, spacing: 2) {
                    Text(metadata.displayPath)
                        .font(.body)

                    if let lastModified = metadata.lastModified {
                        Text(formattedDate(lastModified))
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                Spacer()

                if let language = metadata.language {
                    Text(language.uppercased())
                        .font(.caption2)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.accentColor.opacity(0.2))
                        .cornerRadius(4)
                }
            }
        }
        .onAppear {
            if metadata.language == "python" {
                viewModel.loadSymbolsForFile(metadata.path)
            }
        }
    }

    private var iconName: String {
        metadata.isTextFile ? "doc.text" : "doc"
    }

    private var iconColor: Color {
        metadata.language == "python" ? .blue : .gray
    }

    private func formattedDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }

    private func binding(for filePath: String) -> Binding<Set<String>> {
        Binding(
            get: {
                guard viewModel.currentSession?.selectionState.selectedFile == filePath else {
                    return Set()
                }
                return Set(viewModel.currentSession?.selectionState.selectedItems ?? [])
            },
            set: { newValue in
                viewModel.updateSelection(file: filePath, items: Array(newValue))
            }
        )
    }
}

struct SymbolListView: View {
    let symbols: FileSymbols
    @Binding var selectedItems: Set<String>

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            if !symbols.classes.isEmpty {
                Text("Classes")
                    .font(.caption)
                    .foregroundColor(.secondary)

                ForEach(symbols.classes, id: \.self) { className in
                    Toggle(isOn: Binding(
                        get: { selectedItems.contains(className) },
                        set: { isSelected in
                            if isSelected {
                                selectedItems.insert(className)
                            } else {
                                selectedItems.remove(className)
                            }
                        }
                    )) {
                        HStack {
                            Image(systemName: "c.square")
                                .foregroundColor(.purple)
                            Text(className)
                                .font(.caption)
                        }
                    }
                    .toggleStyle(.checkbox)
                }
            }

            if !symbols.functions.isEmpty {
                Text("Functions")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.top, 4)

                ForEach(symbols.functions, id: \.self) { functionName in
                    Toggle(isOn: Binding(
                        get: { selectedItems.contains(functionName) },
                        set: { isSelected in
                            if isSelected {
                                selectedItems.insert(functionName)
                            } else {
                                selectedItems.remove(functionName)
                            }
                        }
                    )) {
                        HStack {
                            Image(systemName: "function")
                                .foregroundColor(.green)
                            Text(functionName)
                                .font(.caption)
                        }
                    }
                    .toggleStyle(.checkbox)
                }
            }
        }
        .padding(.leading)
    }
}

// MARK: - Drop Zone View

struct DropZoneView: View {
    @Binding var isDragOver: Bool
    let onDrop: ([NSItemProvider]) -> Bool

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "arrow.down.doc")
                .font(.system(size: 48))
                .foregroundColor(.secondary)

            Text("Drop files here")
                .font(.title2)
                .foregroundColor(.secondary)

            Text("or click + to add files")
                .font(.body)
                .foregroundColor(.tertiary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(isDragOver ? Color.accentColor.opacity(0.1) : Color.clear)
    }
}

struct DragOverlayView: View {
    var body: some View {
        RoundedRectangle(cornerRadius: 8)
            .strokeBorder(style: StrokeStyle(lineWidth: 2, dash: [10]))
            .foregroundColor(.accentColor)
            .padding(4)
            .background(Color.accentColor.opacity(0.05))
    }
}

// MARK: - Output Preview View

struct OutputPreviewView: View {
    @ObservedObject var viewModel: FileKittyViewModel

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Preview")
                    .font(.headline)
                Spacer()
                if viewModel.isProcessing {
                    ProgressView()
                        .scaleEffect(0.7)
                }
            }
            .padding()

            Divider()

            // Content
            if let outputText = viewModel.currentSession?.outputText {
                SyntaxHighlightedTextView(text: outputText)
            } else {
                Text("No preview available")
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
    }
}

#Preview {
    ContentView()
}
