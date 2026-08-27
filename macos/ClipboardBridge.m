#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>

static void fail(NSString *reason) {
    fprintf(stderr, "clipboard_status=failed\nreason=%s\n", reason.UTF8String);
    exit(EXIT_FAILURE);
}

static NSString *pixelSize(NSImage *image) {
    NSSize size = image.size;
    return [NSString stringWithFormat:@"%ldx%ld",
            lround(size.width), lround(size.height)];
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 3 || strcmp(argv[1], "set-and-verify") != 0) {
            fail(@"usage: clipboard-bridge set-and-verify /absolute/path/to/image.png");
        }

        NSString *path = [[NSString stringWithUTF8String:argv[2]]
            stringByStandardizingPath];
        NSData *inputData = [NSData dataWithContentsOfFile:path];
        NSImage *inputImage = inputData ? [[NSImage alloc] initWithData:inputData] : nil;
        NSBitmapImageRep *inputBitmap = nil;
        NSData *inputPNG = nil;
        NSData *inputTIFF = inputImage.TIFFRepresentation;
        if (inputTIFF) {
            inputBitmap = [[NSBitmapImageRep alloc] initWithData:inputTIFF];
            inputPNG = [inputBitmap representationUsingType:NSBitmapImageFileTypePNG
                                                    properties:@{}];
        }
        if (!inputData || !inputImage || !inputTIFF || !inputPNG) {
            fail([NSString stringWithFormat:@"cannot_read_or_encode_image=%@", path]);
        }

        NSPasteboard *pasteboard = [NSPasteboard generalPasteboard];
        [pasteboard clearContents];

        NSPasteboardItem *item = [[NSPasteboardItem alloc] init];
        [item setData:inputPNG forType:NSPasteboardTypePNG];
        [item setData:inputTIFF forType:NSPasteboardTypeTIFF];
        if (![pasteboard writeObjects:@[item]]) {
            fail(@"cannot_write_image_to_pasteboard");
        }

        NSData *readBackData = [pasteboard dataForType:NSPasteboardTypePNG];
        if (!readBackData) readBackData = [pasteboard dataForType:NSPasteboardTypeTIFF];
        NSImage *readBackImage = readBackData ? [[NSImage alloc] initWithData:readBackData] : nil;
        if (!readBackImage) fail(@"clipboard_does_not_contain_image");

        NSData *readBackTIFF = readBackImage.TIFFRepresentation;
        NSBitmapImageRep *readBackBitmap = readBackTIFF
            ? [[NSBitmapImageRep alloc] initWithData:readBackTIFF] : nil;
        NSData *readBackPNG = readBackBitmap
            ? [readBackBitmap representationUsingType:NSBitmapImageFileTypePNG properties:@{}]
            : nil;
        if (!readBackPNG || ![pixelSize(inputImage) isEqualToString:pixelSize(readBackImage)] ||
            ![readBackPNG isEqualToData:inputPNG]) {
            fail(@"clipboard_image_does_not_match_input");
        }

        NSArray<NSPasteboardType> *types = pasteboard.types ?: @[];
        printf("clipboard_status=verified\n");
        printf("image_types=%s\n", [[types componentsJoinedByString:@","] UTF8String]);
        printf("width_height=%s\n", pixelSize(inputImage).UTF8String);
        return EXIT_SUCCESS;
    }
}
