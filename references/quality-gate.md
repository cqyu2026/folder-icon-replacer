# Candidate quality contract

The shared gate is `scripts/portable-icon-gate.py`, implemented with Python's standard library. PNG decoding verifies chunk CRC, pixel length and supported encoding before measuring alpha. Files need fully transparent pixels and an opaque subject, 15–72% visible coverage, and fully transparent canvas borders. A bounded color/alpha connected-component pass rejects nearly rectangular regions and isolated pixels. `icon-qa.py` adds native 1024-square checks on macOS.

These are conservative heuristics, not proof of semantic background removal. A white subject enclosing a purple rectangle can have perfect alpha outside it: the color-component rectangle test catches the synthetic reproduction. Irregular/soft/noisy residue may escape that test; source comparison and edge/interior preview review must still pass. Legitimate rectangular artwork can be rejected. Do not weaken thresholds or approve an uncertain candidate to avoid this false positive; request a cleaner, clearly shaped PNG. The coverage range is a residue detector, never a visual-design instruction: it must not be used to add a circular crop, mask, frame, or other shape treatment.

Run preparation with `scripts/prepare-icon.py INPUT NEW_STAGING_DIRECTORY`. Files under staging, raw, previews and rejected are diagnostic candidates, never final assets. `awaiting_visual_review` is not delivery success. Preparation does not create positive review records.

The gate can also export previews for a technically passing PNG:

```sh
python3 scripts/portable-icon-gate.py /absolute/candidate.png --preview-dir /absolute/staging/previews
```

Actually inspect source and candidate at 1024, 128 and 64 px on light, dark and checker backgrounds. Look inside the subject, around holes and along edges for original background color, rectangular remnants, fringe pixels, stray text and missing parts. The generated previews use nearest-neighbor sampling to reveal pixels; 1024 is the full-size review for normalized JPEG derivatives.

Only after this review, write `/absolute/candidate.png.review.json`:

```json
{
  "sha256": "actual SHA-256 returned by the gate for this PNG",
  "reviewer": "identity of the human or vision-capable agent that viewed the previews",
  "background_removed": "passed",
  "edges_clean": "passed",
  "subject_intact": "passed",
  "previews_reviewed": "passed"
}
```

Record failures as `failed`, not `passed`; include source path/hash and observations in the run manifest. Missing records, stale hashes, failed checks and unreadable records fail closed. Neither `--require-review` nor `qualify-pack.py` creates approval. Technical failures remain failures even with an affirmative record. An agent may write a reviewer record only after it actually viewed the current previews; it must not infer approval from the user's filename selection, target selection, or request to continue. This is an auditable review attestation, not a cryptographic proof of human sight or a defense against deliberately modified scripts/forged records.

For packs, `source-pack/visual-qa.json` lists filenames and visual coherence results. Each PNG additionally needs its own review sidecar. `qualify-pack.py` reruns the shared gate instead of trusting a `technical_qa` string and removes a previously promoted version if it no longer qualifies. The application wrapper and newly compiled native setter repeat the gate. The native writer checks that image bytes did not change during QA and rechecks target identity before writing.

## Publication and application byte binding (1.3.2)

A technical pass never replaces explicit visual review, including for background patches smaller than the automatic rectangle threshold. A missing record, stale image hash or failed visual decision blocks promotion and every writer. The review must be the result of actually viewing the current file, not an automatically generated approval. This closes the route from an automatic false negative to automatic approval; it does not make incorrect human attestations true.

The gate returns SHA-256 for both the image bytes and the review record bytes it checked. Promotion reads both into memory, checks these hashes, writes those snapshots to a private staging directory and revalidates the staged pair before atomic replacement in final-pack. A change to either source after validation is rejected and quarantined. The writer passes the initially approved image hash into the native setter. The setter checks that the NSImage input data matches both that hash and the freshly executed gate result, then uses the captured data rather than rereading the source image for NSImage. Direct native invocation also binds its captured bytes to the gate result.
