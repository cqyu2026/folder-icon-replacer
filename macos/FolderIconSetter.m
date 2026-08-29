#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <sys/mount.h>
#import <sys/stat.h>

static void fail(NSString *reason) {
    fprintf(stderr, "icon_status=failed\nreason=%s\n", reason.UTF8String);
    exit(EXIT_FAILURE);
}

static BOOL hasProtectedPrefix(NSString *path) {
    NSArray<NSString *> *prefixes = @[@"/System", @"/Library", @"/private", @"/usr", @"/bin", @"/sbin", @"/var"];
    for (NSString *prefix in prefixes) {
        if ([path isEqualToString:prefix] || [path hasPrefix:[prefix stringByAppendingString:@"/"]]) return YES;
    }
    return NO;
}

static void validateFolder(NSString *path) {
    if (![path isAbsolutePath] || [path isEqualToString:@"/"]) fail(@"target_is_not_an_ordinary_folder");

    struct stat targetStat;
    if (lstat(path.fileSystemRepresentation, &targetStat) != 0 || !S_ISDIR(targetStat.st_mode)) {
        fail(@"target_is_not_an_ordinary_folder");
    }
    if (S_ISLNK(targetStat.st_mode)) fail(@"target_symbolic_link_not_allowed");
    if (hasProtectedPrefix(path)) fail(@"target_protected_system_directory");

    NSURL *url = [NSURL fileURLWithPath:path];
    NSNumber *isPackage = nil;
    NSNumber *isUbiquitous = nil;
    [url getResourceValue:&isPackage forKey:NSURLIsPackageKey error:nil];
    [url getResourceValue:&isUbiquitous forKey:NSURLIsUbiquitousItemKey error:nil];
    if (isPackage.boolValue) fail(@"target_package_not_allowed");
    if (isUbiquitous.boolValue) fail(@"target_network_or_special_volume_not_allowed");

    struct statfs volume;
    if (statfs(path.fileSystemRepresentation, &volume) != 0 || !(volume.f_flags & MNT_LOCAL)) {
        fail(@"target_network_or_special_volume_not_allowed");
    }

    NSString *parent = [path stringByDeletingLastPathComponent];
    struct stat parentStat;
    if (stat(parent.fileSystemRepresentation, &parentStat) == 0 && parentStat.st_dev != targetStat.st_dev) {
        fail(@"target_mount_point_not_allowed");
    }
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 4 || strcmp(argv[1], "set-and-verify") != 0) {
            fail(@"usage: folder-icon-setter set-and-verify /absolute/image.png /absolute/folder");
        }

        NSString *imagePath = [[NSString stringWithUTF8String:argv[2]] stringByStandardizingPath];
        NSString *folderPath = [[NSString stringWithUTF8String:argv[3]] stringByStandardizingPath];
        if (![imagePath isAbsolutePath] || ![folderPath isAbsolutePath]) fail(@"paths_must_be_absolute");
        validateFolder(folderPath);

        NSImage *image = [[NSImage alloc] initWithContentsOfFile:imagePath];
        if (!image) fail(@"cannot_decode_icon_image");

        NSWorkspace *workspace = NSWorkspace.sharedWorkspace;
        NSData *before = [workspace iconForFile:folderPath].TIFFRepresentation;
        BOOL set = [workspace setIcon:image forFile:folderPath options:0];
        if (!set) {
            fprintf(stderr, "icon_status=permission_denied\nreason=nsworkspace_rejected_icon_update\n");
            return 13;
        }

        NSData *after = [workspace iconForFile:folderPath].TIFFRepresentation;
        if (!after) {
            fprintf(stderr, "icon_status=uncertain\nreason=cannot_read_back_folder_icon\n");
            return 14;
        }
        if (before && [before isEqualToData:after]) fail(@"folder_icon_did_not_change");

        printf("icon_status=verified\n");
        printf("target=%s\n", folderPath.UTF8String);
        printf("backend=NSWorkspace.setIcon\n");
        return EXIT_SUCCESS;
    }
}
