#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <sys/mount.h>
#import <sys/stat.h>
#import <CommonCrypto/CommonDigest.h>

static void fail(NSString *reason) { fprintf(stderr, "icon_status=failed\nreason=%s\n", reason.UTF8String); exit(EXIT_FAILURE); }
static NSString *sha256(NSData *data) {
    unsigned char digest[CC_SHA256_DIGEST_LENGTH]; CC_SHA256(data.bytes, (CC_LONG)data.length, digest);
    NSMutableString *hex = [NSMutableString string];
    for (NSUInteger i = 0; i < sizeof(digest); i++) [hex appendFormat:@"%02x", digest[i]];
    return hex;
}
static NSData *iconPixels(NSImage *image) {
    NSBitmapImageRep *bitmap = [[NSBitmapImageRep alloc] initWithBitmapDataPlanes:NULL pixelsWide:128 pixelsHigh:128 bitsPerSample:8 samplesPerPixel:4 hasAlpha:YES isPlanar:NO colorSpaceName:NSDeviceRGBColorSpace bytesPerRow:0 bitsPerPixel:0];
    [NSGraphicsContext saveGraphicsState]; [NSGraphicsContext setCurrentContext:[NSGraphicsContext graphicsContextWithBitmapImageRep:bitmap]];
    [[NSColor clearColor] set]; NSRectFill(NSMakeRect(0, 0, 128, 128)); [image drawInRect:NSMakeRect(0, 0, 128, 128) fromRect:NSZeroRect operation:NSCompositingOperationSourceOver fraction:1.0];
    [NSGraphicsContext restoreGraphicsState]; return [NSData dataWithBytes:bitmap.bitmapData length:bitmap.bytesPerRow * bitmap.pixelsHigh];
}
static BOOL protectedPath(NSString *path) { for (NSString *p in @[@"/System", @"/Library", @"/private", @"/usr", @"/bin", @"/sbin", @"/var"]) if ([path isEqualToString:p] || [path hasPrefix:[p stringByAppendingString:@"/"]]) return YES; return NO; }
static void rejectSymlinks(NSString *path) { NSString *current = @"/"; for (NSString *part in path.pathComponents) { if ([part isEqualToString:@"/"]) continue; current = [current stringByAppendingPathComponent:part]; struct stat s; if (lstat(current.fileSystemRepresentation, &s) != 0) fail(@"target_path_component_not_accessible"); if (S_ISLNK(s.st_mode)) fail(@"target_path_contains_symbolic_link"); } }
static NSString *validate(NSString *path, unsigned long long device, unsigned long long inode) {
    if (![path isAbsolutePath] || [path isEqualToString:@"/"] || protectedPath(path)) fail(@"target_not_allowed");
    rejectSymlinks(path); struct stat s; if (lstat(path.fileSystemRepresentation, &s) != 0 || !S_ISDIR(s.st_mode)) fail(@"target_is_not_directory");
    if ((unsigned long long)s.st_dev != device || (unsigned long long)s.st_ino != inode) fail(@"target_identity_changed");
    struct statfs volume; if (statfs(path.fileSystemRepresentation, &volume) != 0 || !(volume.f_flags & MNT_LOCAL)) fail(@"target_is_not_local_volume");
    NSString *parent = [path stringByDeletingLastPathComponent]; struct stat parentInfo; if (stat(parent.fileSystemRepresentation, &parentInfo) == 0 && parentInfo.st_dev != s.st_dev) fail(@"target_is_mount_point");
    NSURL *url = [NSURL fileURLWithPath:path]; NSNumber *isPackage = nil; [url getResourceValue:&isPackage forKey:NSURLIsPackageKey error:nil]; BOOL app = [[path.pathExtension lowercaseString] isEqualToString:@"app"];
    if (isPackage.boolValue || app) fail(@"target_package_not_allowed"); return @"folder";
}
int main(int argc, const char *argv[]) { @autoreleasepool {
    if (argc != 7 || strcmp(argv[1], "set-and-verify") != 0) fail(@"usage: folder-icon-replacer set-and-verify image target expected-device expected-inode approved-sha256");
    NSString *image = [[NSString stringWithUTF8String:argv[2]] stringByStandardizingPath]; NSString *target = [[NSString stringWithUTF8String:argv[3]] stringByStandardizingPath];
    if (![image isAbsolutePath] || ![target isAbsolutePath]) fail(@"paths_must_be_absolute");
    unsigned long long expectedDevice = strtoull(argv[4], NULL, 10);
    unsigned long long expectedInode = strtoull(argv[5], NULL, 10);
    NSString *type = validate(target, expectedDevice, expectedInode);
    NSData *imageBytes = [NSData dataWithContentsOfFile:image];
    if (!imageBytes || ![sha256(imageBytes) isEqualToString:[NSString stringWithUTF8String:argv[6]]]) fail(@"image_changed_after_check");
    validate(target, expectedDevice, expectedInode);
    NSImage *input = [[NSImage alloc] initWithData:imageBytes]; if (!input) fail(@"cannot_decode_icon_image"); NSWorkspace *workspace = NSWorkspace.sharedWorkspace;
    NSData *before = [workspace iconForFile:target].TIFFRepresentation; if (![workspace setIcon:input forFile:target options:0]) { fprintf(stderr, "icon_status=permission_denied\nreason=nsworkspace_rejected_icon_update\n"); return 13; }
    struct stat afterStat; if (lstat(target.fileSystemRepresentation, &afterStat) != 0 ||
        ((unsigned long long)afterStat.st_dev != expectedDevice || (unsigned long long)afterStat.st_ino != expectedInode)) {
        fprintf(stderr, "icon_status=uncertain\nreason=target_identity_changed_after_write\n"); return 14;
    }
    NSImage *afterImage = [workspace iconForFile:target]; NSData *after = afterImage.TIFFRepresentation; if (!after || !afterImage) { fprintf(stderr, "icon_status=uncertain\nreason=cannot_read_back_folder_icon\n"); return 14; }
    if (before && [before isEqualToData:after]) {
        NSData *selected = iconPixels(input), *current = iconPixels(afterImage);
        if (selected && current && [selected isEqualToData:current]) {
            printf("icon_status=already_selected\ntarget=%s\ntarget_type=%s\nbackend=NSWorkspace.setIcon\n", target.UTF8String, type.UTF8String); return EXIT_SUCCESS;
        }
        fprintf(stderr, "icon_status=uncertain\nreason=folder_icon_did_not_change\n"); return 14;
    }
    if (![iconPixels(input) isEqualToData:iconPixels(afterImage)]) {
        fprintf(stderr, "icon_status=uncertain\nreason=readback_pixels_differ\n"); return 14;
    }
    printf("icon_status=verified\ntarget=%s\ntarget_type=%s\nbackend=NSWorkspace.setIcon\n", target.UTF8String, type.UTF8String); return EXIT_SUCCESS;
} }
