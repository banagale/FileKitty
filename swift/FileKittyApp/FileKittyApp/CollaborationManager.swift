//
//  CollaborationManager.swift
//  FileKittyApp
//
//  Real-time collaborative session sharing
//

import Foundation
import MultipeerConnectivity

class CollaborationManager: NSObject, ObservableObject {
    @Published var isSharing = false
    @Published var connectedPeers: [MCPeerID] = []
    @Published var receivedSession: PromptSession?

    private let serviceType = "filekitty-sync"
    private let myPeerId = MCPeerID(displayName: Host.current().localizedName ?? "FileKitty User")
    private var session: MCSession!
    private var advertiser: MCNearbyServiceAdvertiser!
    private var browser: MCNearbyServiceBrowser!

    override init() {
        super.init()

        session = MCSession(peer: myPeerId, securityIdentity: nil, encryptionPreference: .required)
        session.delegate = self

        advertiser = MCNearbyServiceAdvertiser(peer: myPeerId, discoveryInfo: nil, serviceType: serviceType)
        advertiser.delegate = self

        browser = MCNearbyServiceBrowser(peer: myPeerId, serviceType: serviceType)
        browser.delegate = self
    }

    // MARK: - Sharing

    func startSharing() {
        isSharing = true
        advertiser.startAdvertisingPeer()
        browser.startBrowsingForPeers()
    }

    func stopSharing() {
        isSharing = false
        advertiser.stopAdvertisingPeer()
        browser.stopBrowsingForPeers()
        session.disconnect()
        connectedPeers.removeAll()
    }

    func shareSession(_ promptSession: PromptSession) {
        guard !connectedPeers.isEmpty else { return }

        do {
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601
            let data = try encoder.encode(promptSession)

            try session.send(data, toPeers: connectedPeers, with: .reliable)
        } catch {
            print("Error sharing session: \(error)")
        }
    }

    func shareSelectionUpdate(_ selectionState: SelectionState) {
        guard !connectedPeers.isEmpty else { return }

        do {
            let encoder = JSONEncoder()
            let updateData: [String: Any] = [
                "type": "selection_update",
                "data": [
                    "mode": selectionState.mode,
                    "selected_file": selectionState.selectedFile as Any,
                    "selected_items": selectionState.selectedItems,
                ],
            ]

            let jsonData = try JSONSerialization.data(withJSONObject: updateData)
            try session.send(jsonData, toPeers: connectedPeers, with: .reliable)
        } catch {
            print("Error sharing selection: \(error)")
        }
    }

    private func handleReceivedData(_ data: Data) {
        // Try to decode as full session
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        if let session = try? decoder.decode(PromptSession.self, from: data) {
            DispatchQueue.main.async {
                self.receivedSession = session
            }
            return
        }

        // Try to decode as update
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let type = json["type"] as? String,
           type == "selection_update"
        {
            // Handle selection update
            NotificationCenter.default.post(
                name: .collaborativeSelectionUpdate,
                object: nil,
                userInfo: json["data"] as? [String: Any]
            )
        }
    }
}

// MARK: - MCSessionDelegate

extension CollaborationManager: MCSessionDelegate {
    func session(_ session: MCSession, peer peerID: MCPeerID, didChange state: MCSessionState) {
        DispatchQueue.main.async {
            self.connectedPeers = session.connectedPeers
        }
    }

    func session(_ session: MCSession, didReceive data: Data, fromPeer peerID: MCPeerID) {
        handleReceivedData(data)
    }

    func session(_ session: MCSession, didReceive stream: InputStream, withName streamName: String, fromPeer peerID: MCPeerID) {}

    func session(
        _ session: MCSession,
        didStartReceivingResourceWithName resourceName: String,
        fromPeer peerID: MCPeerID,
        with progress: Progress
    ) {}

    func session(
        _ session: MCSession,
        didFinishReceivingResourceWithName resourceName: String,
        fromPeer peerID: MCPeerID,
        at localURL: URL?,
        withError error: Error?
    ) {}
}

// MARK: - MCNearbyServiceAdvertiserDelegate

extension CollaborationManager: MCNearbyServiceAdvertiserDelegate {
    func advertiser(_ advertiser: MCNearbyServiceAdvertiser, didReceiveInvitationFromPeer peerID: MCPeerID, withContext context: Data?, invitationHandler: @escaping (Bool, MCSession?) -> Void) {
        // Auto-accept invitations
        invitationHandler(true, session)
    }
}

// MARK: - MCNearbyServiceBrowserDelegate

extension CollaborationManager: MCNearbyServiceBrowserDelegate {
    func browser(_ browser: MCNearbyServiceBrowser, foundPeer peerID: MCPeerID, withDiscoveryInfo info: [String: String]?) {
        // Auto-invite discovered peers
        browser.invitePeer(peerID, to: session, withContext: nil, timeout: 30)
    }

    func browser(_ browser: MCNearbyServiceBrowser, lostPeer peerID: MCPeerID) {
        print("Lost peer: \(peerID.displayName)")
    }
}

extension Notification.Name {
    static let collaborativeSelectionUpdate = Notification.Name("collaborativeSelectionUpdate")
}
