//
//  CloudSyncManager.swift
//  FileKittyApp
//
//  iCloud sync for sessions and preferences
//

import Foundation
import CloudKit

class CloudSyncManager: ObservableObject {
    static let shared = CloudSyncManager()

    private let container: CKContainer
    private let privateDatabase: CKDatabase
    @Published var isSyncing = false
    @Published var syncError: Error?

    private init() {
        container = CKContainer(identifier: "iCloud.com.bastet.FileKitty")
        privateDatabase = container.privateCloudDatabase
    }

    func setup() {
        // Request permission and setup sync
        checkAccountStatus()
    }

    private func checkAccountStatus() {
        container.accountStatus { status, error in
            if let error = error {
                print("iCloud account error: \(error)")
                return
            }

            switch status {
            case .available:
                print("iCloud available")
                self.setupSubscriptions()
            case .noAccount:
                print("No iCloud account")
            case .restricted:
                print("iCloud restricted")
            case .couldNotDetermine:
                print("Could not determine iCloud status")
            case .temporarilyUnavailable:
                print("iCloud temporarily unavailable")
            @unknown default:
                print("Unknown iCloud status")
            }
        }
    }

    private func setupSubscriptions() {
        // Subscribe to session changes
        let predicate = NSPredicate(value: true)
        let subscription = CKQuerySubscription(
            recordType: "Session",
            predicate: predicate,
            options: [.firesOnRecordCreation, .firesOnRecordUpdate, .firesOnRecordDeletion]
        )

        let notificationInfo = CKSubscription.NotificationInfo()
        notificationInfo.shouldSendContentAvailable = true
        subscription.notificationInfo = notificationInfo

        privateDatabase.save(subscription) { _, error in
            if let error = error {
                print("Subscription error: \(error)")
            }
        }
    }

    // MARK: - Session Sync

    func saveSession(_ session: PromptSession) async throws {
        isSyncing = true
        defer { isSyncing = false }

        let record = CKRecord(recordType: "Session", recordID: CKRecord.ID(recordName: session.id))

        // Encode session to JSON
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        let jsonData = try encoder.encode(session)

        record["sessionData"] = jsonData as CKRecordValue
        record["timestamp"] = session.timestamp as CKRecordValue
        record["projectRoot"] = (session.projectRoot ?? "") as CKRecordValue

        try await privateDatabase.save(record)
    }

    func loadSession(id: String) async throws -> PromptSession {
        isSyncing = true
        defer { isSyncing = false }

        let recordID = CKRecord.ID(recordName: id)
        let record = try await privateDatabase.record(for: recordID)

        guard let jsonData = record["sessionData"] as? Data else {
            throw CloudSyncError.invalidData
        }

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(PromptSession.self, from: jsonData)
    }

    func fetchAllSessions() async throws -> [PromptSession] {
        isSyncing = true
        defer { isSyncing = false }

        let query = CKQuery(recordType: "Session", predicate: NSPredicate(value: true))
        query.sortDescriptors = [NSSortDescriptor(key: "timestamp", ascending: false)]

        let (results, _) = try await privateDatabase.records(matching: query)

        var sessions: [PromptSession] = []

        for (_, result) in results {
            switch result {
            case .success(let record):
                if let jsonData = record["sessionData"] as? Data {
                    let decoder = JSONDecoder()
                    decoder.dateDecodingStrategy = .iso8601
                    if let session = try? decoder.decode(PromptSession.self, from: jsonData) {
                        sessions.append(session)
                    }
                }
            case .failure(let error):
                print("Error loading session: \(error)")
            }
        }

        return sessions
    }

    func deleteSession(id: String) async throws {
        isSyncing = true
        defer { isSyncing = false }

        let recordID = CKRecord.ID(recordName: id)
        try await privateDatabase.deleteRecord(withID: recordID)
    }

    // MARK: - Preferences Sync

    func savePreferences(_ settings: FileKittySettings) async throws {
        let record = CKRecord(recordType: "Preferences", recordID: CKRecord.ID(recordName: "userPreferences"))

        let encoder = JSONEncoder()
        let jsonData = try encoder.encode(settings)

        record["settingsData"] = jsonData as CKRecordValue
        record["lastModified"] = Date() as CKRecordValue

        try await privateDatabase.save(record)
    }

    func loadPreferences() async throws -> FileKittySettings {
        let recordID = CKRecord.ID(recordName: "userPreferences")
        let record = try await privateDatabase.record(for: recordID)

        guard let jsonData = record["settingsData"] as? Data else {
            throw CloudSyncError.invalidData
        }

        let decoder = JSONDecoder()
        return try decoder.decode(FileKittySettings.self, from: jsonData)
    }
}

enum CloudSyncError: Error {
    case invalidData
    case notAvailable
    case syncFailed
}
