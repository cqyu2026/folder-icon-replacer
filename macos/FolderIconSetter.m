#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>

static void fail(NSString *reason) {
    fprintf(stderr, "icon_status=failed\nreason=%s\n", reason.UTF8String);
    exit(EXIT_FAILURE);
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 4 || strcmp(argv[1], "set-and-verify") != 0) {
            fail(@"usage: folder-icon-setter set-and-verify /absolute/image.png /absolute/folder");
        }

        NSString *imagePath = [[NSString stringWithUTF8String:argv[2]] stringByStandardizingPath];
        NSString *folderPath = [[NSString stringWithUTF8String:argv[3]] stringByStandardizingPath];
        BOOL isDirectory = NO;
        if (![NSFileManager.defaultManager fileExistsAtPath:folderPath isDirectory:&isDirectory] || !isDirectory) {
            fail(@"target_is_not_a_directory");
        }
        if (![folderPath isAbsolutePath] || ![imagePath isAbsolutePath]) fail(@"paths_must_be_absolute");

        NSImage *image = [[NSImage alloc] initWithContentsOfFile:imagePath];
        if (!image) fail(@"cannot_decode_icon_image");

        NSWorkspace *workspace = NSWorkspace.sharedWorkspace;
        NSData *before = [workspace iconForFile:folderPath].TIFFRepresentation;
        BOOL set = [workspace setIcon:image forFile:folderPath options:0];
        if (!set) fail(@"nsworkspace_rejected_icon_update");

        NSData *after = [workspace iconForFile:folderPath].TIFFRepresentation;
        if (!after) fail(@"cannot_read_back_folder_icon");
        if (before && [before isEqualToData:after]) fail(@"folder_icon_did_not_change");

        printf("icon_status=verified\n");
        printf("target=%s\n", folderPath.UTF8String);
        printf("backend=NSWorkspace.setIcon\n");
        return EXIT_SUCCESS;
    }
}
