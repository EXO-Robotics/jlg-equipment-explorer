# Model assets

`600s.glb` is the accepted structural blockout v0.1. It passes the hierarchy,
articulation, selection, desktop, and mobile viewer gates, but it is not the
optimized production model.

Its immutable validation record is `600s.asset-receipt.json`; the template
remains the contract for future asset revisions. The authored Blender source is
kept outside the deployable model directory at
`source/blender/600s-blockout-v0.1.blend`.

Do not commit manufacturer BIM, commercial reference meshes, proprietary CAD, or any source asset whose license does not explicitly allow modification and public redistribution.

Recommended future layout:

```text
models/
├── 600s.glb
├── 600aj.glb
└── es1930m.glb
```

Keep authored Blender sources outside the deployable web directory or in a clearly separated `source/` directory with their own provenance record.
