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
        NSDictionary *properties = CFBridgingRelease(CGImageSourceCopyPropertiesAtIndex(source, 0, NULL));
        id profile = properties[(NSString *)kCGImagePropertyProfileName];
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
        size_t visibleCount = 0;
        size_t minX = width;
        size_t minY = height;
        size_t maxX = 0;
        size_t maxY = 0;
        BOOL touchesCanvasEdge = NO;
        for (size_t y = 0; y < height; y++) {
            unsigned char *row = pixels + y * bytesPerRow;
            for (size_t x = 0; x < width; x++) {
                unsigned int alpha = row[x * 4 + 3];
                if (alpha < alphaMin) alphaMin = alpha;
                if (alpha > alphaMax) alphaMax = alpha;
                if (alpha > 0) {
                    visibleCount++;
                    if (x < minX) minX = x;
                    if (y < minY) minY = y;
                    if (x > maxX) maxX = x;
                    if (y > maxY) maxY = y;
                    if (x == 0 || y == 0 || x == width - 1 || y == height - 1) touchesCanvasEdge = YES;
                }
            }
        }

        NSString *type = sourceType ? (__bridge NSString *)sourceType : @"unknown";
        BOOL isPNG = [type isEqualToString:@"public.png"];
        NSDictionary *result = @{
            @"status": @"ok",
            @"path": path,
            @"type": type,
            @"color_space_name": (__bridge id)CGColorSpaceGetName(CGImageGetColorSpace(image)) ?: [NSNull null],
            @"has_icc_profile": @(profile != nil),
            @"is_png": @(isPNG),
            @"width": @(width),
            @"height": @(height),
            @"alpha_min": @(alphaMin),
            @"alpha_max": @(alphaMax),
            @"has_transparent_pixels": @(alphaMin < 255),
            @"has_visible_pixels": @(alphaMax > 0),
            @"corner_alpha": @[@(pixels[3]), @(pixels[(width - 1) * 4 + 3]), @(pixels[(height - 1) * bytesPerRow + 3]), @(pixels[(height - 1) * bytesPerRow + (width - 1) * 4 + 3])],
            @"visible_coverage": @((double)visibleCount / (double)(width * height)),
            @"visible_bounds": alphaMax > 0 ? @{ @"min_x": @(minX), @"min_y": @(minY), @"max_x": @(maxX), @"max_y": @(maxY) } : [NSNull null],
            @"touches_canvas_edge": @(touchesCanvasEdge)
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
