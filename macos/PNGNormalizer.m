#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>
#import <ImageIO/ImageIO.h>

static void fail(NSString *reason) { fprintf(stderr, "normalize_status=failed\nreason=%s\n", reason.UTF8String); exit(EXIT_FAILURE); }
int main(int argc, const char *argv[]) { @autoreleasepool {
    if (argc != 3) fail(@"usage: png-normalizer input output");
    NSURL *inURL = [NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[1]]];
    NSURL *outURL = [NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[2]]];
    CGImageSourceRef source = CGImageSourceCreateWithURL((__bridge CFURLRef)inURL, NULL);
    CGImageRef image = source ? CGImageSourceCreateImageAtIndex(source, 0, NULL) : NULL;
    if (!image) fail(@"cannot_decode_image");
    size_t w = CGImageGetWidth(image), h = CGImageGetHeight(image); if (!w || !h) fail(@"invalid_dimensions");
    size_t content = 820; CGFloat scale = MIN((CGFloat)content / w, (CGFloat)content / h);
    size_t dw = MAX(1, (size_t)llround(w * scale)), dh = MAX(1, (size_t)llround(h * scale));
    unsigned char *pixels = calloc(1024 * 1024 * 4, 1); CGColorSpaceRef cs = CGColorSpaceCreateWithName(kCGColorSpaceSRGB);
    CGContextRef ctx = CGBitmapContextCreate(pixels, 1024, 1024, 8, 4096, cs, kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big);
    if (!ctx) fail(@"cannot_create_rgba_context");
    CGContextDrawImage(ctx, CGRectMake((1024-dw)/2, (1024-dh)/2, dw, dh), image);
    CGImageRef output = CGBitmapContextCreateImage(ctx); CGImageDestinationRef dest = CGImageDestinationCreateWithURL((__bridge CFURLRef)outURL, CFSTR("public.png"), 1, NULL);
    if (!dest || !output) fail(@"cannot_create_png_destination");
    CGImageDestinationAddImage(dest, output, NULL); if (!CGImageDestinationFinalize(dest)) fail(@"cannot_write_png");
    printf("normalize_status=verified\noutput=%s\nwidth=1024\nheight=1024\ncolor_space=sRGB\nalpha=RGBA\n", outURL.path.UTF8String);
    CFRelease(dest); CGImageRelease(output); CGContextRelease(ctx); CGColorSpaceRelease(cs); free(pixels); CGImageRelease(image); CFRelease(source); return 0;
} }
