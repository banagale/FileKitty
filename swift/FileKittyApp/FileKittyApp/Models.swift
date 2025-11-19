//
//  Models.swift
//  FileKittyApp
//
//  Data models matching Python backend structures
//

import Foundation

// MARK: - Request/Response Models

struct APIRequest: Codable {
    let action: String
    let sessionId: String
    let payload: [String: AnyCodable]
    let timestamp: String

    enum CodingKeys: String, CodingKey {
        case action
        case sessionId = "session_id"
        case payload
        case timestamp
    }
}

struct APIResponse: Codable {
    let action: String
    let sessionId: String
    let success: Bool
    let payload: [String: AnyCodable]?
    let error: ErrorResponse?
    let timestamp: String

    enum CodingKeys: String, CodingKey {
        case action
        case sessionId = "session_id"
        case success
        case payload
        case error
        case timestamp
    }
}

struct ErrorResponse: Codable {
    let type: String
    let message: String
    let details: [String: AnyCodable]?
    let debug: String?
}

// MARK: - Domain Models

struct FileMetadata: Codable, Identifiable, Hashable {
    var id: String { path }
    let path: String
    let displayPath: String
    let isTextFile: Bool
    let language: String?
    let lastModified: Date?
    let fileHash: String?
    let sizeBytes: Int?

    enum CodingKeys: String, CodingKey {
        case path
        case displayPath = "display_path"
        case isTextFile = "is_text_file"
        case language
        case lastModified = "last_modified"
        case fileHash = "file_hash"
        case sizeBytes = "size_bytes"
    }
}

struct TreeSnapshot: Codable, Hashable {
    let basePath: String
    let basePathDisplay: String
    let ignoreRegex: String
    let rendered: String

    enum CodingKeys: String, CodingKey {
        case basePath = "base_path"
        case basePathDisplay = "base_path_display"
        case ignoreRegex = "ignore_regex"
        case rendered
    }
}

struct SelectionState: Codable, Hashable {
    var mode: String // "All Files" or "Single File"
    var selectedFile: String?
    var selectedItems: [String] // Classes/functions

    enum CodingKeys: String, CodingKey {
        case mode
        case selectedFile = "selected_file"
        case selectedItems = "selected_items"
    }

    init(mode: String = "All Files", selectedFile: String? = nil, selectedItems: [String] = []) {
        self.mode = mode
        self.selectedFile = selectedFile
        self.selectedItems = selectedItems
    }
}

struct PromptSession: Codable, Identifiable, Hashable {
    var id: String
    let timestamp: Date
    let files: [String]
    let fileMetadata: [FileMetadata]
    var selectionState: SelectionState
    let projectRoot: String?
    let treeSnapshot: TreeSnapshot?
    var outputText: String?
    let settings: [String: AnyCodable]

    enum CodingKeys: String, CodingKey {
        case id
        case timestamp
        case files
        case fileMetadata = "file_metadata"
        case selectionState = "selection_state"
        case projectRoot = "project_root"
        case treeSnapshot = "tree_snapshot"
        case outputText = "output_text"
        case settings
    }
}

struct PythonSymbols: Codable {
    let symbols: [String: FileSymbols]
    let errors: [SymbolError]
}

struct FileSymbols: Codable {
    let classes: [String]
    let functions: [String]
}

struct SymbolError: Codable {
    let file: String
    let error: String
}

// MARK: - Settings

struct FileKittySettings: Codable {
    var includeTree: Bool = true
    var treeBaseDir: String = ""
    var treeIgnoreRegex: String = "\\.git|\\.pyc|__pycache__|\\.DS_Store"
    var includeDateModified: Bool = true
    var autoCopy: Bool = false

    enum CodingKeys: String, CodingKey {
        case includeTree = "include_tree"
        case treeBaseDir = "tree_base_dir"
        case treeIgnoreRegex = "tree_ignore_regex"
        case includeDateModified = "include_date_modified"
        case autoCopy = "auto_copy"
    }
}

// MARK: - AnyCodable Helper

struct AnyCodable: Codable, Hashable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let string = try? container.decode(String.self) {
            value = string
        } else if let array = try? container.decode([AnyCodable].self) {
            value = array.map { $0.value }
        } else if let dict = try? container.decode([String: AnyCodable].self) {
            value = dict.mapValues { $0.value }
        } else {
            value = NSNull()
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()

        switch value {
        case let bool as Bool:
            try container.encode(bool)
        case let int as Int:
            try container.encode(int)
        case let double as Double:
            try container.encode(double)
        case let string as String:
            try container.encode(string)
        case let array as [Any]:
            try container.encode(array.map { AnyCodable($0) })
        case let dict as [String: Any]:
            try container.encode(dict.mapValues { AnyCodable($0) })
        default:
            try container.encodeNil()
        }
    }

    func hash(into hasher: inout Hasher) {
        switch value {
        case let bool as Bool:
            hasher.combine(bool)
        case let int as Int:
            hasher.combine(int)
        case let double as Double:
            hasher.combine(double)
        case let string as String:
            hasher.combine(string)
        default:
            hasher.combine(0)
        }
    }

    static func == (lhs: AnyCodable, rhs: AnyCodable) -> Bool {
        switch (lhs.value, rhs.value) {
        case let (lhs as Bool, rhs as Bool):
            return lhs == rhs
        case let (lhs as Int, rhs as Int):
            return lhs == rhs
        case let (lhs as Double, rhs as Double):
            return lhs == rhs
        case let (lhs as String, rhs as String):
            return lhs == rhs
        default:
            return false
        }
    }
}
