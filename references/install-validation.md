# Installation validation

Use the installed complete package. No test needs the author's workspace or a real user folder.

Portable tests require only Python 3 and the standard library:

```sh
python3 tests/test_portable_icon_gate.py
python3 tests/test_pack_qualification.py
python3 tests/test_route_pack_fixtures.py
python3 tests/test_pack_route.py
python3 scripts/install-self-test.py --stage preflight
```

Portable fixtures cover opaque and padded rectangles, purple rectangle inside a white subject, isolated/edge pixels, corrupt PNG, missing/stale visual records, clean transparent PNG and JPEG rejection with transparent-PNG guidance. Positive synthetic attestations in tests are not approval of user images.

On a capable Mac, with authorization to write a temporary fixture's icon:

```sh
python3 tests/test_native_gate.py
python3 tests/test_mvp_builder_guard.py
python3 scripts/install-self-test.py --stage e2e --authorize-e2e
python3 scripts/run-mvp-validation.py --runtime /absolute/new-test-runtime --output /absolute/new-test-output
python3 scripts/prepare-icon.py tests/skill-test-image.jpg /absolute/new-jpeg-staging
```

The native e2e uses a synthetic transparent PNG, never raw JPEG. The MVP retains direct PNG, generated-pack, route and unsafe-target checks using local copies of packaged fixtures. JPEG preparation retains the real Vision → ImageIO normalization → technical QA → awaiting visual review chain; then actually inspect previews before recording review or attempting isolated application. A failed extraction is a failure with safe fallback, not a skipped success.

`native-ready` proves compilation only; `verified` requires icon write/readback and fixture-only content comparison. Production code never performs that content comparison. Test-created files belong in the chosen test directory; do not use real target folders as permission probes.
