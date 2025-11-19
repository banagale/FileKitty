//
//  PreviewProvider.swift
//  FileKittyQuickLook
//
//  Quick Look preview provider for .filekitty session files
//

import QuickLook
import SwiftUI

class PreviewProvider: QLPreviewProvider, QLPreviewingController {
    func providePreview(for request: QLFileRequest) async throws -> QLPreviewReply {
        let fileURL = request.fileURL

        // Load and parse session file
        let data = try Data(contentsOf: fileURL)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let session = try decoder.decode(PromptSession.self, from: data)

        // Create preview
        return QLPreviewReply(dataOfContentType: .pdf, contentSize: CGSize(width: 800, height: 1000)) { reply in
            // Render SwiftUI view to PDF
            let view = SessionPreviewView(session: session)
            let renderer = ImageRenderer(content: view.frame(width: 800, height: 1000))

            if let cgImage = renderer.cgImage {
                let image = NSImage(cgImage: cgImage, size: NSSize(width: 800, height: 1000))

                // Create PDF data
                let pdfData = NSMutableData()
                if let consumer = CGDataConsumer(data: pdfData as CFMutableData),
                   let pdfContext = CGContext(consumer: consumer, mediaBox: nil, nil)
                {
                    pdfContext.beginPDFPage(nil)
                    let nsGraphicsContext = NSGraphicsContext(cgContext: pdfContext, flipped: false)
                    NSGraphicsContext.current = nsGraphicsContext

                    image.draw(in: CGRect(x: 0, y: 0, width: 800, height: 1000))

                    pdfContext.endPDFPage()
                    pdfContext.closePDF()

                    try pdfData.write(to: reply.url)
                }
            }

            return reply.url
        }
    }
}

// MARK: - Preview View

struct SessionPreviewView: View {
    let session: PromptSession

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Header
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "cat.fill")
                        .font(.title)
                        .foregroundColor(.accentColor)

                    Text("FileKitty Session")
                        .font(.title)
                        .fontWeight(.bold)
                }

                if let projectRoot = session.projectRoot {
                    Text(URL(fileURLWithPath: projectRoot).lastPathComponent)
                        .font(.title2)
                        .foregroundColor(.secondary)
                }

                HStack {
                    Label("\(session.files.count) files", systemImage: "doc")
                    Spacer()
                    Text(formattedDate(session.timestamp))
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .font(.caption)
            }
            .padding()
            .background(Color.secondary.opacity(0.1))
            .cornerRadius(8)

            // Files list
            VStack(alignment: .leading, spacing: 8) {
                Text("Files")
                    .font(.headline)

                ForEach(session.fileMetadata.prefix(10)) { metadata in
                    HStack {
                        Image(systemName: metadata.isTextFile ? "doc.text" : "doc")
                            .foregroundColor(.blue)

                        Text(metadata.displayPath)
                            .font(.caption)
                            .lineLimit(1)

                        Spacer()

                        if let language = metadata.language {
                            Text(language.uppercased())
                                .font(.caption2)
                                .padding(.horizontal, 4)
                                .padding(.vertical, 2)
                                .background(Color.accentColor.opacity(0.2))
                                .cornerRadius(4)
                        }
                    }
                }

                if session.files.count > 10 {
                    Text("+ \(session.files.count - 10) more files")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            // Selection state
            if session.selectionState.mode == "Single File" {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Selection")
                        .font(.headline)

                    if let selectedFile = session.selectionState.selectedFile {
                        Text("File: \(selectedFile)")
                            .font(.caption)
                    }

                    if !session.selectionState.selectedItems.isEmpty {
                        Text("Items: \(session.selectionState.selectedItems.joined(separator: ", "))")
                            .font(.caption)
                            .lineLimit(2)
                    }
                }
            }

            // Preview snippet
            if let outputText = session.outputText {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Output Preview")
                        .font(.headline)

                    Text(String(outputText.prefix(500)))
                        .font(.system(.caption, design: .monospaced))
                        .lineLimit(15)
                        .padding()
                        .background(Color.secondary.opacity(0.05))
                        .cornerRadius(4)

                    if outputText.count > 500 {
                        Text("...")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }

            Spacer()
        }
        .padding()
    }

    private func formattedDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}
