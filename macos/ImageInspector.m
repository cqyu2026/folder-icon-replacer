#import <Foundation/Foundation.h>
#import <ImageIO/ImageIO.h>
#import <CoreGraphics/CoreGraphics.h>

static void emitFailure(NSString *reason) {
    NSDictionary *result = @{ @"status": @"failed", @"reason": reason };
    NSData *data = [NSJSONSerialization dataWithJSONObject:result options:0 error:nil];
    fwrite(data.bytes, 1, data.length, stdout);
    fputc('\n', stdout);
    exit(EXIT_FAILURE);
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 2) emitFailure(@"usage: image-inspector /absolute/path/to/image");

        NSString *path = [[NSString stringWithUTF8String:argv[1]] stringByStandardizingPath];
        NSURL *url = [NSURL fileURLWithPath:path];
        CGImageSourceRef source = CGImageSourceCreateWithURL((__bridge CFURLRef)url, NULL);
        if (!source) emitFailure(@"cannot_decode_image");

        CFStringRef sourceType = CGImageSourceGetType(source);
        CGImageRef image = CGImageSourceCreateImageAtIndex(source, 0, NULL);
        if (!image) {
            CFRelease(source);
            emitFailure(@"cannot_read_first_frame");
        }

        size_t width = CGImageGetWidth(image);
        size_t height = CGImageGetHeight(image);
        if (width == 0 || height == 0 || width > SIZE_MAX / 4 || height > SIZE_MAX / (width * 4)) {
            CGImageRelease(image);
            CFRelease(source);
            emitFailure(@"invalid_image_dimensions");
        }

        size_t bytesPerRow = width * 4;
        unsigned char *pixels = calloc(height, bytesPerRow);
        CGColorSpaceRef colorSpace = CGColorSpaceCreateWithName(kCGColorSpaceSRGB);
        CGContextRef context = CGBitmapContextCreate(
            pixels, width, height, 8, bytesPerRow, colorSpace,
            kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big
        );
        if (!pixels || !context) {
            if (context) CGContextRelease(context);
            if (pixels) free(pixels);
            CGColorSpaceRelease(colorSpace);
            CGImageRelease(image);
            CFRelease(source);
            emitFailure(@"cannot_create_rgba_buffer");
        }

        CGContextDrawImage(context, CGRectMake(0, 0, width, height), image);
        unsigned int alphaMin = 255;
        unsigned int alphaMax = 0;
        for (size_t y = 0; y < height; y++) {
            unsigned char *row = pixels + y * bytesPerRow;
            for (size_t x = 0; x < width; x++) {
                unsigned int alpha = row[x * 4 + 3];
                if (alpha < alphaMin) alphaMin = alpha;
                if (alpha > alphaMax) alphaMax = alpha;
            }
        }

        NSString *type = sourceType ? (__bridge NSString *)sourceType : @"unknown";
        BOOL isPNG = [type isEqualToString:@"public.png"];
        NSDictionary *result = @{
            @"status": @"ok",
            @"path": path,
            @"type": type,
            @"is_png": @(isPNG),
            @"width": @(width),
            @"height": @(height),
            @"alpha_min": @(alphaMin),
            @"alpha_max": @(alphaMax),
            @"has_transparent_pixels": @(alphaMin < 255),
            @"has_visible_pixels": @(alphaMax > 0)
        };
        NSData *data = [NSJSONSerialization dataWithJSONObject:result options:0 error:nil];
        fwrite(data.bytes, 1, data.length, stdout);
        fputc('\n', stdout);

        CGContextRelease(context);
        free(pixels);
        CGColorSpaceRelease(colorSpace);
        CGImageRelease(image);
        CFRelease(source);
        return EXIT_SUCCESS;
    }
}
