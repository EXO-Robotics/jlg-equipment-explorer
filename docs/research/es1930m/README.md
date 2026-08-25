# ES1930M showcase milestone

The direct local route is `/es1930m/`. `/600s/` is a compatibility redirect to the existing root 600S viewer, so the legacy public URL remains unchanged during the multi-machine transition.

Run the ES1930M gates directly from the repository root:

```sh
node --check viewer/runtime.js
node --check machines/es1930m/articulation.js
node --check machines/es1930m/machine.js
python3 -B scripts/validate_es1930m_evidence.py
python3 -B scripts/validate_es1930m_kinematics.py
python3 -B scripts/validate_es1930m_glb.py
python3 -B scripts/validate_es1930m_receipt.py
```

To verify locally retained official PDF binaries as well as their frozen hashes:

```sh
python3 -B scripts/validate_es1930m_evidence.py --sources-dir tmp/es1930m
```

`VISUAL_COMPARISON.md` records the fixed-view review, first-party coverage gaps, and known reconstruction deviations. Regenerate its four local stowed comparison views with Blender using `scripts/render_es1930m_preview.py`; the images stay under ignored `tmp/es1930m/review-renders/` and are not redistributed.

After an intentional Blender export, update `machines/es1930m/version.js` with the exact GLB SHA-256 and regenerate the candidate receipt with `python3 -B scripts/write_es1930m_receipt.py`.

The receipt intentionally remains `candidate_not_deployable` until the branch is pushed by authorization, GitHub Pages deploys it, and the deployed route is reviewed. `python3 -B scripts/validate_es1930m_receipt.py --require-release` must continue to fail until that external gate is genuinely complete.
