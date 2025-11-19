//
//  SyntaxHighlightedTextView.swift
//  FileKittyApp
//
//  Syntax-highlighted markdown preview
//

import SwiftUI
import AppKit

struct SyntaxHighlightedTextView: NSViewRepresentable {
    let text: String

    func makeNSView(context: Context) -> NSScrollView {
        let scrollView = NSTextView.scrollableTextView()
        let textView = scrollView.documentView as! NSTextView

        textView.isEditable = false
        textView.isSelectable = true
        textView.font = NSFont.monospacedSystemFont(ofSize: 13, weight: .regular)
        textView.textContainerInset = NSSize(width: 10, height: 10)

        return scrollView
    }

    func updateNSView(_ scrollView: NSScrollView, context: Context) {
        guard let textView = scrollView.documentView as? NSTextView else { return }

        let attributedString = highlightMarkdown(text)
        textView.textStorage?.setAttributedString(attributedString)
    }

    private func highlightMarkdown(_ text: String) -> NSAttributedString {
        let attributedString = NSMutableAttributedString(string: text)
        let range = NSRange(location: 0, length: (text as NSString).length)

        // Base styling
        let baseFont = NSFont.monospacedSystemFont(ofSize: 13, weight: .regular)
        let textColor = NSColor.textColor

        attributedString.addAttribute(.font, value: baseFont, range: range)
        attributedString.addAttribute(.foregroundColor, value: textColor, range: range)

        // Highlight code blocks
        highlightCodeBlocks(in: attributedString, text: text)

        // Highlight headers
        highlightHeaders(in: attributedString, text: text)

        // Highlight inline code
        highlightInlineCode(in: attributedString, text: text)

        return attributedString
    }

    private func highlightCodeBlocks(in attributedString: NSMutableAttributedString, text: String) {
        let pattern = "```(\\w+)?\\n([\\s\\S]*?)```"
        guard let regex = try? NSRegularExpression(pattern: pattern) else { return }

        let range = NSRange(location: 0, length: (text as NSString).length)
        let matches = regex.matches(in: text, range: range)

        for match in matches.reversed() {
            let fullRange = match.range
            let codeRange = match.range(at: 2)

            // Background for code block
            attributedString.addAttribute(
                .backgroundColor,
                value: NSColor.textBackgroundColor.withAlphaComponent(0.5),
                range: fullRange
            )

            // Syntax highlighting for code
            if codeRange.location != NSNotFound {
                let languageRange = match.range(at: 1)
                var language = "text"

                if languageRange.location != NSNotFound {
                    language = (text as NSString).substring(with: languageRange)
                }

                let code = (text as NSString).substring(with: codeRange)
                highlightCode(code, language: language, in: attributedString, range: codeRange)
            }
        }
    }

    private func highlightCode(_ code: String, language: String, in attributedString: NSMutableAttributedString, range: NSRange) {
        let codeFont = NSFont.monospacedSystemFont(ofSize: 12, weight: .regular)
        attributedString.addAttribute(.font, value: codeFont, range: range)

        guard language == "python" else { return }

        // Python syntax highlighting (simple)
        let keywords = ["def", "class", "import", "from", "return", "if", "else", "elif", "for", "while", "try", "except", "finally", "with", "as", "pass", "break", "continue", "raise", "assert", "yield", "async", "await", "lambda", "None", "True", "False"]

        for keyword in keywords {
            let pattern = "\\b\(keyword)\\b"
            if let regex = try? NSRegularExpression(pattern: pattern) {
                let matches = regex.matches(in: code, range: NSRange(location: 0, length: code.count))

                for match in matches {
                    let keywordRange = NSRange(
                        location: range.location + match.range.location,
                        length: match.range.length
                    )
                    attributedString.addAttribute(.foregroundColor, value: NSColor.systemPurple, range: keywordRange)
                    attributedString.addAttribute(.font, value: NSFont.monospacedSystemFont(ofSize: 12, weight: .bold), range: keywordRange)
                }
            }
        }

        // Highlight strings
        let stringPattern = "(\"([^\"\\\\]|\\\\.)*\"|'([^'\\\\]|\\\\.)*')"
        if let stringRegex = try? NSRegularExpression(pattern: stringPattern) {
            let matches = stringRegex.matches(in: code, range: NSRange(location: 0, length: code.count))

            for match in matches {
                let stringRange = NSRange(
                    location: range.location + match.range.location,
                    length: match.range.length
                )
                attributedString.addAttribute(.foregroundColor, value: NSColor.systemGreen, range: stringRange)
            }
        }

        // Highlight comments
        let commentPattern = "#.*$"
        if let commentRegex = try? NSRegularExpression(pattern: commentPattern, options: .anchorsMatchLines) {
            let matches = commentRegex.matches(in: code, range: NSRange(location: 0, length: code.count))

            for match in matches {
                let commentRange = NSRange(
                    location: range.location + match.range.location,
                    length: match.range.length
                )
                attributedString.addAttribute(.foregroundColor, value: NSColor.systemGray, range: commentRange)
            }
        }
    }

    private func highlightHeaders(in attributedString: NSMutableAttributedString, text: String) {
        let pattern = "^(#{1,6})\\s+(.+)$"
        guard let regex = try? NSRegularExpression(pattern: pattern, options: .anchorsMatchLines) else { return }

        let range = NSRange(location: 0, length: (text as NSString).length)
        let matches = regex.matches(in: text, range: range)

        for match in matches {
            let headerRange = match.range

            // Calculate font size based on header level
            let hashesRange = match.range(at: 1)
            let hashes = (text as NSString).substring(with: hashesRange)
            let level = hashes.count

            let fontSize: CGFloat = CGFloat(20 - (level * 2))
            let headerFont = NSFont.boldSystemFont(ofSize: fontSize)

            attributedString.addAttribute(.font, value: headerFont, range: headerRange)
            attributedString.addAttribute(.foregroundColor, value: NSColor.systemBlue, range: headerRange)
        }
    }

    private func highlightInlineCode(in attributedString: NSMutableAttributedString, text: String) {
        let pattern = "`([^`]+)`"
        guard let regex = try? NSRegularExpression(pattern: pattern) else { return }

        let range = NSRange(location: 0, length: (text as NSString).length)
        let matches = regex.matches(in: text, range: range)

        for match in matches.reversed() {
            let codeRange = match.range

            attributedString.addAttribute(
                .backgroundColor,
                value: NSColor.textBackgroundColor.withAlphaComponent(0.5),
                range: codeRange
            )
            attributedString.addAttribute(
                .font,
                value: NSFont.monospacedSystemFont(ofSize: 12, weight: .regular),
                range: codeRange
            )
        }
    }
}
