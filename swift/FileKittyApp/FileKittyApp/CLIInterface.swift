//
//  CLIInterface.swift
//  FileKittyApp
//
//  Handles communication with Python CLI backend
//

import Foundation

enum CLIError: Error {
    case pythonNotFound
    case processError(String)
    case invalidResponse(String)
    case backendError(ErrorResponse)
}

class CLIInterface: ObservableObject {
    private let pythonPath: String
    private let cliScript: String
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    init() {
        // Configure date decoding strategy
        decoder.dateDecodingStrategy = .iso8601
        encoder.dateEncodingStrategy = .iso8601

        // Find Python executable
        pythonPath = Self.findPython()

        // Find CLI script
        cliScript = Self.findCLIScript()
    }

    // MARK: - API Methods

    func processFiles(
        files: [URL],
        selectionState: SelectionState = SelectionState(),
        settings: FileKittySettings = FileKittySettings()
    ) async throws -> PromptSession {
        let filePaths = files.map { $0.path }

        let payload: [String: AnyCodable] = [
            "files": AnyCodable(filePaths),
            "selection_state": AnyCodable([
                "mode": selectionState.mode,
                "selected_file": selectionState.selectedFile as Any,
                "selected_items": selectionState.selectedItems,
            ]),
            "settings": AnyCodable([
                "include_tree": settings.includeTree,
                "tree_base_dir": settings.treeBaseDir,
                "tree_ignore_regex": settings.treeIgnoreRegex,
                "include_date_modified": settings.includeDateModified,
                "auto_copy": settings.autoCopy,
            ]),
        ]

        let response = try await executeAction("process_files", payload: payload)

        guard let sessionDict = response.payload?["prompt_session"]?.value as? [String: Any] else {
            throw CLIError.invalidResponse("Missing prompt_session in response")
        }

        let sessionData = try JSONSerialization.data(withJSONObject: sessionDict)
        return try decoder.decode(PromptSession.self, from: sessionData)
    }

    func getPythonSymbols(files: [URL]) async throws -> PythonSymbols {
        let filePaths = files.map { $0.path }

        let payload: [String: AnyCodable] = [
            "files": AnyCodable(filePaths)
        ]

        let response = try await executeAction("get_python_symbols", payload: payload)

        guard let payloadDict = response.payload else {
            throw CLIError.invalidResponse("Missing payload in response")
        }

        let payloadData = try JSONSerialization.data(withJSONObject: payloadDict.mapValues { $0.value })
        return try decoder.decode(PythonSymbols.self, from: payloadData)
    }

    func updateSelection(sessionId: String, selectionState: SelectionState) async throws -> String {
        let payload: [String: AnyCodable] = [
            "selection_state": AnyCodable([
                "mode": selectionState.mode,
                "selected_file": selectionState.selectedFile as Any,
                "selected_items": selectionState.selectedItems,
            ])
        ]

        let response = try await executeAction("update_selection", payload: payload, sessionId: sessionId)

        guard let outputText = response.payload?["output_text"]?.value as? String else {
            throw CLIError.invalidResponse("Missing output_text in response")
        }

        return outputText
    }

    func saveSession(sessionId: String, toFile fileURL: URL) async throws {
        let payload: [String: AnyCodable] = [
            "file_path": AnyCodable(fileURL.path)
        ]

        _ = try await executeAction("save_session", payload: payload, sessionId: sessionId)
    }

    func loadSession(fromFile fileURL: URL, sessionId: String? = nil) async throws -> PromptSession {
        let sid = sessionId ?? UUID().uuidString

        let payload: [String: AnyCodable] = [
            "file_path": AnyCodable(fileURL.path)
        ]

        let response = try await executeAction("load_session", payload: payload, sessionId: sid)

        guard let sessionDict = response.payload?["prompt_session"]?.value as? [String: Any] else {
            throw CLIError.invalidResponse("Missing prompt_session in response")
        }

        let sessionData = try JSONSerialization.data(withJSONObject: sessionDict)
        return try decoder.decode(PromptSession.self, from: sessionData)
    }

    // MARK: - Private Methods

    private func executeAction(_ action: String, payload: [String: AnyCodable], sessionId: String? = nil) async throws -> APIResponse {
        let sid = sessionId ?? UUID().uuidString

        let request: [String: Any] = [
            "action": action,
            "session_id": sid,
            "payload": payload.mapValues { $0.value },
            "timestamp": ISO8601DateFormatter().string(from: Date()),
        ]

        let requestData = try JSONSerialization.data(withJSONObject: request)
        let requestJSON = String(data: requestData, encoding: .utf8)!

        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments = ["-m", "filekitty.cli_interface", action, "--session-id", sid]

        let inputPipe = Pipe()
        let outputPipe = Pipe()
        let errorPipe = Pipe()

        process.standardInput = inputPipe
        process.standardOutput = outputPipe
        process.standardError = errorPipe

        try process.run()

        // Write request to stdin
        inputPipe.fileHandleForWriting.write(requestData)
        try inputPipe.fileHandleForWriting.close()

        // Read response
        let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
        let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()

        process.waitUntilExit()

        if process.terminationStatus != 0 {
            let errorString = String(data: errorData, encoding: .utf8) ?? "Unknown error"
            throw CLIError.processError(errorString)
        }

        let response = try decoder.decode(APIResponse.self, from: outputData)

        if !response.success, let error = response.error {
            throw CLIError.backendError(error)
        }

        return response
    }

    private static func findPython() -> String {
        // Try common Python paths
        let paths = [
            "/usr/bin/python3",
            "/usr/local/bin/python3",
            "/opt/homebrew/bin/python3",
            ProcessInfo.processInfo.environment["PYTHON_PATH"] ?? "",
        ]

        for path in paths where FileManager.default.fileExists(atPath: path) {
            return path
        }

        // Fallback to searching PATH
        return "python3"
    }

    private static func findCLIScript() -> String {
        // Try to find the installed CLI script
        let paths = [
            "/usr/local/bin/filekitty-cli",
            "/opt/homebrew/bin/filekitty-cli",
            ProcessInfo.processInfo.environment["FILEKITTY_CLI"] ?? "",
        ]

        for path in paths where FileManager.default.fileExists(atPath: path) {
            return path
        }

        return "filekitty-cli"
    }
}
