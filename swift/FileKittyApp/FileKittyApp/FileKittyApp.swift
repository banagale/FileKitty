//
//  FileKittyApp.swift
//  FileKittyApp
//
//  Main application entry point
//

import SwiftUI

@main
struct FileKittyApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var menuBarManager = MenuBarManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(menuBarManager)
                .onAppear {
                    setupWindow()
                }
        }
        .commands {
            FileKittyCommands()
        }
        .defaultSize(width: 1200, height: 800)

        #if os(macOS)
        Settings {
            SettingsView(settings: .constant(FileKittySettings()))
        }
        #endif
    }

    private func setupWindow() {
        // Configure window appearance
        if let window = NSApp.windows.first {
            window.titlebarAppearsTransparent = false
            window.toolbarStyle = .unified
        }
    }
}

// MARK: - App Delegate

class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Setup iCloud sync if available
        CloudSyncManager.shared.setup()
    }

    func application(_ application: NSApplication, open urls: [URL]) {
        // Handle file opening
        for url in urls {
            if url.pathExtension == "filekitty" {
                NotificationCenter.default.post(
                    name: .openSessionFile,
                    object: nil,
                    userInfo: ["url": url]
                )
            }
        }
    }
}

// MARK: - Custom Commands

struct FileKittyCommands: Commands {
    var body: some Commands {
        CommandGroup(replacing: .newItem) {
            Button("New Session") {
                NotificationCenter.default.post(name: .createNewSession, object: nil)
            }
            .keyboardShortcut("n", modifiers: .command)

            Button("Open Files...") {
                NotificationCenter.default.post(name: .openFiles, object: nil)
            }
            .keyboardShortcut("o", modifiers: .command)

            Divider()

            Button("Load Session...") {
                NotificationCenter.default.post(name: .loadSession, object: nil)
            }
            .keyboardShortcut("o", modifiers: [.command, .shift])
        }

        CommandGroup(after: .newItem) {
            Button("Command Palette...") {
                NotificationCenter.default.post(name: .showCommandPalette, object: nil)
            }
            .keyboardShortcut("k", modifiers: .command)
        }

        CommandMenu("Session") {
            Button("Export Session...") {
                NotificationCenter.default.post(name: .exportSession, object: nil)
            }
            .keyboardShortcut("s", modifiers: [.command, .shift])

            Button("Share Session...") {
                NotificationCenter.default.post(name: .shareSession, object: nil)
            }

            Divider()

            Button("Copy Output") {
                NotificationCenter.default.post(name: .copyOutput, object: nil)
            }
            .keyboardShortcut("c", modifiers: [.command, .shift])
        }
    }
}

// MARK: - Notification Names

extension Notification.Name {
    static let createNewSession = Notification.Name("createNewSession")
    static let openFiles = Notification.Name("openFiles")
    static let loadSession = Notification.Name("loadSession")
    static let exportSession = Notification.Name("exportSession")
    static let shareSession = Notification.Name("shareSession")
    static let copyOutput = Notification.Name("copyOutput")
    static let showCommandPalette = Notification.Name("showCommandPalette")
    static let openSessionFile = Notification.Name("openSessionFile")
}
