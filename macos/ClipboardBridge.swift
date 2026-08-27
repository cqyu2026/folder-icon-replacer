import AppKit
import CryptoKit
import Foundation

enum BridgeError: Error, CustomStringConvertible {
    case invalidArguments
    case unreadableImage(String)
    case cannotEncodeImage
    case clipboardHasNoImage
    case clipboardImageMismatch

    var description: String {
        switch self {
        case .invalidArguments: return "usage: clipboard-bridge set-and-verify /absolute/path/to/image.png"
        case .unreadableImage(let path): return "cannot_read_image=\(path)"
        case .cannotEncodeImage: return "cannot_encode_image"
        case .clipboardHasNoImage: return "clipboard_does_not_contain_image"
        case .clipboardImageMismatch: return "clipboard_image_does_not_match_input"
        }
    }
}

func sha256(_ data: Data) -> String {
    SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
}

func pixelSize(_ image: NSImage) -> String {
    let size = image.size
    return "\(Int(size.width.rounded()))x\(Int(size.height.rounded()))"
}

func fail(_ error: Error) -> Never {
    fputs("clipboard_status=failed\nreason=\(error)\n", stderr)
    exit(1)
}

guard CommandLine.arguments.count == 3,
      CommandLine.arguments[1] == "set-and-verify" else {
    fail(BridgeError.invalidArguments)
}

let inputPath = CommandLine.arguments[2]
let inputURL = URL(fileURLWithPath: inputPath).standardizedFileURL
guard let inputData = try? Data(contentsOf: inputURL),
      let inputImage = NSImage(data: inputData),
      let inputSource = inputImage.tiffRepresentation,
      let inputBitmap = NSBitmapImageRep(data: inputSource),
      let inputPNG = inputBitmap.representation(using: .png, properties: [:]) else {
    fail(BridgeError.unreadableImage(inputURL.path))
}

let pasteboard = NSPasteboard.general
pasteboard.clearContents()

let item = NSPasteboardItem()
guard item.setData(inputPNG, forType: .png),
      item.setData(inputSource, forType: .tiff),
      pasteboard.writeObjects([item]) else {
    fail(BridgeError.cannotEncodeImage)
}

let availableTypes = pasteboard.types ?? []
let readBackData = pasteboard.data(forType: .png) ?? pasteboard.data(forType: .tiff)
guard let readBackData,
      let readBackImage = NSImage(data: readBackData) else {
    fail(BridgeError.clipboardHasNoImage)
}

let readBackSource = readBackImage.tiffRepresentation
let readBackBitmap = readBackSource.flatMap(NSBitmapImageRep.init(data:))
let readBackPNG = readBackBitmap?.representation(using: .png, properties: [:])
guard pixelSize(inputImage) == pixelSize(readBackImage),
      readBackPNG == inputPNG else {
    fail(BridgeError.clipboardImageMismatch)
}

print("clipboard_status=verified")
print("image_types=\(availableTypes.map(\.rawValue).joined(separator: ","))")
print("width_height=\(pixelSize(inputImage))")
print("digest=\(sha256(inputPNG))")
