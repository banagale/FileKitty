//
//  ShortcutsProvider.swift
//  FileKittyApp
//
//  Shortcuts integration for automation
//

import Foundation
import AppIntents

// MARK: - Process Files Intent

@available(macOS 13.0, *)
struct ProcessFilesIntent: AppIntent {
    static var title: LocalizedStringResource = "Process Files with FileKitty"
    static var description = IntentDescription("Process files and generate markdown output")

    @Parameter(title: "Files", description: "Files to process")
    var files: [IntentFile]

    @Parameter(title: "Include Tree", description: "Include folder tree in output", default: true)
    var includeTree: Bool

    @Parameter(title: "Include Dates", description: "Include last modified dates", default: true)
    var includeDates: Bool

    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        let fileURLs = files.compactMap { $0.fileURL }

        let settings = FileKittySettings(
            includeTree: includeTree,
            includeDateModified: includeDates
        )

        let cliInterface = CLIInterface()
        let session = try await cliInterface.processFiles(
            files: fileURLs,
            settings: settings
        )

        return .result(value: session.outputText ?? "")
    }
}

// MARK: - Get Python Symbols Intent

@available(macOS 13.0, *)
struct GetPythonSymbolsIntent: AppIntent {
    static var title: LocalizedStringResource = "Get Python Symbols"
    static var description = IntentDescription("Extract classes and functions from Python files")

    @Parameter(title: "Python Files", description: "Python files to analyze")
    var files: [IntentFile]

    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        let fileURLs = files.compactMap { $0.fileURL }

        let cliInterface = CLIInterface()
        let symbols = try await cliInterface.getPythonSymbols(files: fileURLs)

        // Format output
        var output = "# Python Symbols\n\n"

        for (file, fileSymbols) in symbols.symbols {
            output += "## \(URL(fileURLWithPath: file).lastPathComponent)\n\n"

            if !fileSymbols.classes.isEmpty {
                output += "### Classes\n"
                for className in fileSymbols.classes {
                    output += "- \(className)\n"
                }
                output += "\n"
            }

            if !fileSymbols.functions.isEmpty {
                output += "### Functions\n"
                for functionName in fileSymbols.functions {
                    output += "- \(functionName)\n"
                }
                output += "\n"
            }
        }

        return .result(value: output)
    }
}

// MARK: - Load Session Intent

@available(macOS 13.0, *)
struct LoadSessionIntent: AppIntent {
    static var title: LocalizedStringResource = "Load FileKitty Session"
    static var description = IntentDescription("Load a saved FileKitty session")

    @Parameter(title: "Session File", description: "FileKitty session file to load")
    var sessionFile: IntentFile

    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        guard let fileURL = sessionFile.fileURL else {
            throw IntentError.message("Invalid file")
        }

        let cliInterface = CLIInterface()
        let session = try await cliInterface.loadSession(fromFile: fileURL)

        return .result(value: session.outputText ?? "")
    }
}

// MARK: - Save Session Intent

@available(macOS 13.0, *)
struct SaveSessionIntent: AppIntent {
    static var title: LocalizedStringResource = "Save FileKitty Session"
    static var description = IntentDescription("Save current FileKitty session")

    @Parameter(title: "Session ID", description: "ID of session to save")
    var sessionId: String

    @Parameter(title: "Output File", description: "File to save session to")
    var outputFile: IntentFile

    func perform() async throws -> some IntentResult {
        guard let fileURL = outputFile.fileURL else {
            throw IntentError.message("Invalid output file")
        }

        let cliInterface = CLIInterface()
        try await cliInterface.saveSession(sessionId: sessionId, toFile: fileURL)

        return .result()
    }
}

// MARK: - App Shortcuts Provider

@available(macOS 13.0, *)
struct FileKittyShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: ProcessFilesIntent(),
            phrases: [
                "Process files with \(.applicationName)",
                "Generate context with \(.applicationName)",
            ],
            shortTitle: "Process Files",
            systemImageName: "doc.text.magnifyingglass"
        )

        AppShortcut(
            intent: GetPythonSymbolsIntent(),
            phrases: [
                "Get Python symbols with \(.applicationName)",
                "Analyze Python files with \(.applicationName)",
            ],
            shortTitle: "Get Symbols",
            systemImageName: "function"
        )

        AppShortcut(
            intent: LoadSessionIntent(),
            phrases: [
                "Load session with \(.applicationName)",
            ],
            shortTitle: "Load Session",
            systemImageName: "folder"
        )
    }
}

enum IntentError: Error, LocalizedError {
    case message(String)

    var errorDescription: String? {
        switch self {
        case .message(let msg):
            return msg
        }
    }
}
