# Material Pack Workflow

Use this workflow only after the user chooses “generate a material pack.”

## Image-tool boundary and composition

Use only an image-generation or image-editing capability already available and suitable for the requested source material. If none exists, stop after reporting that limitation; do not install packages or implement an ad-hoc crop, mask, or rendering pipeline. `scripts/build-mvp-pack.py` is exclusively a deterministic test-fixture builder: it requires `--fixture-only` and accepts only the packaged fixture.

The quality gate's coverage limit detects unwanted opaque background. It does not prescribe a circular icon or any other shape. Do not crop a photo into a circle, apply a mask or frame, or change the requested composition unless the user explicitly requests that treatment and reviews the resulting candidate.

## Routing

- Use wallpaper-element mode when the image has three or more clear, independently readable objects.
- Use visual-DNA mode when it has one clear subject. Derive visible shape, color, material, or associated objects without cropping a face or inferring identity.
- Use folder-semantic mode for abstract, low-information, or anchorless imagery. Only this mode uses a folder as the default main object.

When the user does not specify a quantity, generate four icons for abstract imagery, five for a general subject, and nine only when the user explicitly requests a complete multi-folder story. Larger packs require a user-supplied semantic mapping.

## Unified visual language gate

Treat the wallpaper as the style master. Before an icon is eligible for `final-pack/`, verify side-by-side that it matches the wallpaper's medium (for example, photographic, painterly, paper-cut, or flat vector), palette, contour softness, texture grain, shadow/highlight treatment, and abstraction level. A pack with mixed photorealistic, flat-vector, or unrelated rendering styles fails even when every file is technically valid. Regenerate the outlier; do not normalize the mismatch by merely changing color.

## Final pack contract

Every candidate must also pass [the shared quality gate](quality-gate.md) with an actual SHA-256-bound visual review sidecar. Keep candidates under `source-pack/generations` until `qualify-pack.py` promotes them. A technical QA string alone is insufficient.

```
<pack-root>/
├── final-pack/
│   ├── final-wallpaper.png
│   ├── icon-01.png
│   └── manifest.md
└── source-pack/
    ├── generations/
    └── previews/
```

Each final icon must be a 1024×1024 sRGB RGBA PNG with transparent corners and a readable 64 px and 128 px preview. Reject RGB checkerboard backgrounds, opaque square backdrops, text, logos, and candidates whose primary subject reaches the canvas edge. Transparent corners are a technical condition, not permission to choose a circular crop or to alter composition.

The manifest records source image, selected routing mode, each icon’s filename, suggested meaning, concept signature, and technical QA result. It records design meaning only; never include a user’s real folder path.

For future additions, inspect existing manifest signatures first. A color change, mirror, or minor decoration alone is not a distinct icon.
