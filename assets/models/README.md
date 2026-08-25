# Model assets

`600s.glb` is the M2.1 structural blockout. It passes the hierarchy, stowed
envelope, nested telescope travel, platform leveling, selection, desktop, and
mobile viewer gates, but it is not the optimized production model.

Mechanical facts are generated into `600s.asset-receipt.json` by
`scripts/write_600s_receipt.py`. Browser and visual-review evidence in that
file is recorded separately and is never auto-accepted. The template remains
the schema for future asset revisions. Cache identity lives in
`600s.version.js`. The authored Blender source is
`source/blender/600s-blockout-v0.2.blend`.

Do not commit manufacturer BIM, commercial reference meshes, proprietary CAD, or any source asset whose license does not explicitly allow modification and public redistribution.

Recommended future layout:

```text
models/
├── 600s.glb
├── 600aj.glb
└── es1930m.glb
```

Keep authored Blender sources outside the deployable web directory or in a clearly separated `source/` directory with their own provenance record.
