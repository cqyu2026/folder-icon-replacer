#import <Foundation/Foundation.h>
#import <Vision/Vision.h>
#import <CoreImage/CoreImage.h>
#import <CoreGraphics/CoreGraphics.h>

static void fail(NSString *reason) {
    fprintf(stderr, "foreground_status=failed\nreason=%s\n", reason.UTF8String);
    exit(EXIT_FAILURE);
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 4 || strcmp(argv[1], "extract") != 0) {
            fail(@"usage: foreground-extractor extract /absolute/input /absolute/output-dir");
        }

        if (@available(macOS 14.0, *)) {
            NSString *inputPath = [[NSString stringWithUTF8String:argv[2]] stringByStandardizingPath];
            NSString *outputPath = [[NSString stringWithUTF8String:argv[3]] stringByStandardizingPath];
            NSFileManager *fm = NSFileManager.defaultManager;
            BOOL isDirectory = NO;
            if (![fm fileExistsAtPath:inputPath isDirectory:&isDirectory] || isDirectory) {
                fail(@"input_is_not_a_readable_file");
            }

            NSError *error = nil;
            if (![fm createDirectoryAtPath:outputPath withIntermediateDirectories:YES attributes:nil error:&error]) {
                fail([NSString stringWithFormat:@"cannot_create_output_dir=%@", error.localizedDescription]);
            }

            NSURL *inputURL = [NSURL fileURLWithPath:inputPath];
            VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithURL:inputURL options:@{}];
            VNGenerateForegroundInstanceMaskRequest *request = [[VNGenerateForegroundInstanceMaskRequest alloc] init];
            // Installation validation must also work in hosts that cannot access ANE model assets.
            // CPU-only execution is slower but deterministic across Codex and WorkBuddy sandboxes.
            request.usesCPUOnly = YES;
            if (![handler performRequests:@[request] error:&error]) {
                fail([NSString stringWithFormat:@"vision_request_failed=%@", error.localizedDescription]);
            }
            VNInstanceMaskObservation *observation = request.results.firstObject;
            if (!observation || observation.allInstances.count == 0) fail(@"no_foreground_instances");

            CIContext *ciContext = [CIContext contextWithOptions:nil];
            CGColorSpaceRef colorSpace = CGColorSpaceCreateWithName(kCGColorSpaceSRGB);
            NSMutableArray *candidates = [NSMutableArray array];
            __block NSUInteger displayIndex = 1;
            [observation.allInstances enumerateIndexesUsingBlock:^(NSUInteger instanceIndex, BOOL *stop) {
                NSIndexSet *selected = [NSIndexSet indexSetWithIndex:instanceIndex];
                NSError *maskError = nil;
                CVPixelBufferRef pixelBuffer = [observation
                    generateMaskedImageOfInstances:selected
                    fromRequestHandler:handler
                    croppedToInstancesExtent:YES
                    error:&maskError];
                if (!pixelBuffer) {
                    fail([NSString stringWithFormat:@"masked_image_failed_instance_%lu=%@",
                          (unsigned long)instanceIndex, maskError.localizedDescription]);
                }

                NSString *filename = [NSString stringWithFormat:@"candidate-%02lu.png", (unsigned long)displayIndex];
                NSString *candidatePath = [outputPath stringByAppendingPathComponent:filename];
                NSURL *candidateURL = [NSURL fileURLWithPath:candidatePath];
                CIImage *ciImage = [CIImage imageWithCVPixelBuffer:pixelBuffer];
                NSError *writeError = nil;
                BOOL wrote = [ciContext writePNGRepresentationOfImage:ciImage
                                                                 toURL:candidateURL
                                                                format:kCIFormatRGBA8
                                                            colorSpace:colorSpace
                                                               options:@{}
                                                                 error:&writeError];
                CVPixelBufferRelease(pixelBuffer);
                if (!wrote) {
                    fail([NSString stringWithFormat:@"cannot_write_candidate_%lu=%@",
                          (unsigned long)displayIndex, writeError.localizedDescription]);
                }
                [candidates addObject:@{
                    @"id": @(displayIndex),
                    @"instance": @(instanceIndex),
                    @"filename": filename,
                    @"path": candidatePath
                }];
                displayIndex++;
            }];
            CGColorSpaceRelease(colorSpace);

            NSDictionary *manifest = @{
                @"schema_version": @1,
                @"source": inputPath,
                @"backend": @"apple-vision-foreground-instance-mask",
                @"candidate_count": @(candidates.count),
                @"candidates": candidates
            };
            NSData *manifestData = [NSJSONSerialization dataWithJSONObject:manifest options:NSJSONWritingPrettyPrinted error:&error];
            NSString *manifestPath = [outputPath stringByAppendingPathComponent:@"candidates.json"];
            if (!manifestData || ![manifestData writeToFile:manifestPath options:NSDataWritingAtomic error:&error]) {
                fail([NSString stringWithFormat:@"cannot_write_manifest=%@", error.localizedDescription]);
            }
            printf("foreground_status=verified\n");
            printf("candidate_count=%lu\n", (unsigned long)candidates.count);
            printf("manifest=%s\n", manifestPath.UTF8String);
            return EXIT_SUCCESS;
        }

        fail(@"apple_vision_requires_macos_14_or_newer");
    }
}
