# macOS Clipboard Bridge

`ClipboardBridge.swift` writes the selected PNG to `NSPasteboard.general` as
image data, reads it back, and refuses to report success unless the decoded
clipboard image matches the input PNG.

The preferred no-Xcode implementation is `ClipboardBridge.m`, compiled with
the Command Line Tools' `clang`:

```sh
clang -framework AppKit -framework Foundation ClipboardBridge.m -o clipboard-bridge
```

Build on macOS:

```sh
swiftc -framework AppKit -framework CryptoKit ClipboardBridge.swift -o clipboard-bridge
```

The compiler and macOS SDK must come from a compatible Apple toolchain. If
Swift reports an SDK/compiler version mismatch, do not use a different copy
operation as a fallback; resolve the toolchain first.

Run:

```sh
./clipboard-bridge set-and-verify /absolute/path/to/final.png
```

The bridge only touches the general clipboard. It does not open Finder and
does not modify folders or their contents.

The Finder workflow must stop unless the command exits with
`clipboard_status=verified`. The executable is architecture-specific; rebuild
it on the target Mac if the installed binary does not match the machine.
