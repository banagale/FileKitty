//
//  FileKittyViewModel.swift
//  FileKittyApp
//
//  Main view model managing app state and business logic
//

import Foundation
import SwiftUI
import Combine

@MainActor
class FileKittyViewModel: ObservableObject {
    @Published var currentSession: PromptSession?
    @Published var sessionHistory: [PromptSession] = []
    @Published var selectedSessionId: String?
    @Published var selectedFiles: Set<String> = []
    @Published var fileSymbols: [String: FileSymbols] = [:]
    @Published var settings = FileKittySettings()
    @Published var isProcessing = false
    @Published var error: Error?

    private let cliInterface = CLIInterface()
    private let historyManager = SessionHistoryManager()
    private var cancellables = Set<AnyCancellable>()

    init() {
        // Load saved settings
        loadSettings()

        // Watch for session changes
        $currentSession
            .sink { [weak self] session in
                if let session = session {
                    self?.selectedSessionId = session.id
                }
            }
            .store(in: &cancellables)
    }

    // MARK: - File Operations

    func openFiles() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        panel.message = "Select files to process"

        panel.begin { [weak self] response in
            guard response == .OK else { return }
            Task {
                await self?.processFiles(panel.urls)
            }
        }
    }

    func processFiles(_ urls: [URL]) async {
        isProcessing = true
        defer { isProcessing = false }

        do {
            let session = try await cliInterface.processFiles(
                files: urls,
                selectionState: currentSession?.selectionState ?? SelectionState(),
                settings: settings
            )

            currentSession = session
            addToHistory(session)
        } catch {
            self.error = error
            print("Error processing files: \(error)")
        }
    }

    func removeFiles(at indexSet: IndexSet) {
        guard var session = currentSession else { return }

        let filesToRemove = indexSet.map { session.files[$0] }
        session.files.removeAll { filesToRemove.contains($0) }
        session.fileMetadata.removeAll { filesToRemove.contains($0.path) }

        currentSession = session

        Task {
            await regenerateOutput()
        }
    }

    func handleDrop(_ providers: [NSItemProvider]) -> Bool {
        var urls: [URL] = []

        for provider in providers {
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, error in
                if let data = item as? Data, let url = URL(dataRepresentation: data, relativeTo: nil) {
                    urls.append(url)
                }
            }
        }

        // Wait a bit for async loading
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
            Task {
                await self.processFiles(urls)
            }
        }

        return true
    }

    // MARK: - Symbol Operations

    func loadSymbolsForFile(_ filePath: String) {
        guard fileSymbols[filePath] == nil else { return }

        Task {
            do {
                let url = URL(fileURLWithPath: filePath)
                let symbols = try await cliInterface.getPythonSymbols(files: [url])

                if let fileSymbol = symbols.symbols[filePath] {
                    fileSymbols[filePath] = fileSymbol
                }
            } catch {
                print("Error loading symbols for \(filePath): \(error)")
            }
        }
    }

    func updateSelection(file: String, items: [String]) {
        guard var session = currentSession else { return }

        session.selectionState.mode = "Single File"
        session.selectionState.selectedFile = file
        session.selectionState.selectedItems = items

        currentSession = session

        Task {
            await regenerateOutput()
        }
    }

    private func regenerateOutput() async {
        guard let session = currentSession else { return }

        isProcessing = true
        defer { isProcessing = false }

        do {
            let outputText = try await cliInterface.updateSelection(
                sessionId: session.id,
                selectionState: session.selectionState
            )

            var updatedSession = session
            updatedSession.outputText = outputText
            currentSession = updatedSession
        } catch {
            self.error = error
            print("Error regenerating output: \(error)")
        }
    }

    // MARK: - Session Management

    func createNewSession() {
        currentSession = nil
        selectedFiles = []
        fileSymbols = [:]
    }

    func loadSession(_ session: PromptSession) {
        currentSession = session
        selectedFiles = Set(session.files)

        // Load symbols for Python files
        for metadata in session.fileMetadata where metadata.language == "python" {
            loadSymbolsForFile(metadata.path)
        }
    }

    func duplicateSession(_ session: PromptSession) {
        var newSession = session
        newSession.id = UUID().uuidString
        newSession.timestamp = Date()

        currentSession = newSession
        addToHistory(newSession)
    }

    func deleteSession(_ session: PromptSession) {
        sessionHistory.removeAll { $0.id == session.id }
        historyManager.deleteSession(sessionId: session.id)

        if currentSession?.id == session.id {
            currentSession = nil
        }
    }

    func loadSessionFromFile() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        panel.allowedContentTypes = [UTType(filenameExtension: "filekitty")!]
        panel.message = "Select a session file to load"

        panel.begin { [weak self] response in
            guard response == .OK, let url = panel.url else { return }

            Task {
                await self?.loadSessionFromURL(url)
            }
        }
    }

    private func loadSessionFromURL(_ url: URL) async {
        isProcessing = true
        defer { isProcessing = false }

        do {
            let session = try await cliInterface.loadSession(fromFile: url)
            currentSession = session
            addToHistory(session)
        } catch {
            self.error = error
            print("Error loading session: \(error)")
        }
    }

    func exportSession(_ session: PromptSession) {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [UTType(filenameExtension: "filekitty")!]
        panel.nameFieldStringValue = "session-\(session.id).filekitty"
        panel.message = "Export session"

        panel.begin { [weak self] response in
            guard response == .OK, let url = panel.url else { return }

            Task {
                await self?.saveSessionToURL(session, url: url)
            }
        }
    }

    private func saveSessionToURL(_ session: PromptSession, url: URL) async {
        isProcessing = true
        defer { isProcessing = false }

        do {
            try await cliInterface.saveSession(sessionId: session.id, toFile: url)
        } catch {
            self.error = error
            print("Error saving session: \(error)")
        }
    }

    func shareSession(_ session: PromptSession) {
        // Create shareable JSON
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]

        do {
            let jsonData = try encoder.encode(session)

            // Create temp file
            let tempURL = FileManager.default.temporaryDirectory
                .appendingPathComponent("session-\(session.id).filekitty")

            try jsonData.write(to: tempURL)

            // Show share sheet
            let picker = NSSharingServicePicker(items: [tempURL])
            picker.show(relativeTo: .zero, of: NSApp.keyWindow!.contentView!, preferredEdge: .minY)
        } catch {
            self.error = error
            print("Error sharing session: \(error)")
        }
    }

    // MARK: - History Management

    func loadHistory() {
        sessionHistory = historyManager.loadHistory()
    }

    private func addToHistory(_ session: PromptSession) {
        // Remove existing entry with same ID
        sessionHistory.removeAll { $0.id == session.id }

        // Add to beginning
        sessionHistory.insert(session, at: 0)

        // Keep only last 50
        if sessionHistory.count > 50 {
            sessionHistory = Array(sessionHistory.prefix(50))
        }

        // Save
        historyManager.saveHistory(sessionHistory)
    }

    // MARK: - Clipboard

    func copyToClipboard() {
        guard let outputText = currentSession?.outputText else { return }

        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(outputText, forType: .string)
    }

    // MARK: - Settings

    private func loadSettings() {
        if let data = UserDefaults.standard.data(forKey: "FileKittySettings"),
           let decoded = try? JSONDecoder().decode(FileKittySettings.self, from: data)
        {
            settings = decoded
        }
    }

    func saveSettings() {
        if let encoded = try? JSONEncoder().encode(settings) {
            UserDefaults.standard.set(encoded, forKey: "FileKittySettings")
        }
    }
}

// MARK: - Session History Manager

class SessionHistoryManager {
    private let historyURL: URL

    init() {
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let appDir = appSupport.appendingPathComponent("FileKitty")

        try? FileManager.default.createDirectory(at: appDir, withIntermediateDirectories: true)

        historyURL = appDir.appendingPathComponent("history.json")
    }

    func loadHistory() -> [PromptSession] {
        guard let data = try? Data(contentsOf: historyURL) else { return [] }

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        return (try? decoder.decode([PromptSession].self, from: data)) ?? []
    }

    func saveHistory(_ sessions: [PromptSession]) {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = .prettyPrinted

        guard let data = try? encoder.encode(sessions) else { return }
        try? data.write(to: historyURL)
    }

    func deleteSession(sessionId: String) {
        var sessions = loadHistory()
        sessions.removeAll { $0.id == sessionId }
        saveHistory(sessions)
    }
}
