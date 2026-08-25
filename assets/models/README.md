# Model assets

`600s.glb` is the v1.1 Accuracy reconstruction. It preserves the verified stowed
envelope while adding the frozen PVC 2607 hierarchy, B3 bodywork, detailed running
gear, three boom sections, visible powertrack and lift cylinder, and the rapid-replace
36 × 96 platform assembly. It remains a portfolio visualization, not an engineering model.
The GLB retains 345 authored meshes for traceability; the viewer consolidates rigid same-material
detail into 80 observed runtime meshes, including runtime presentation marks and hazard-band cues,
without merging articulation or interaction volumes.

Mechanical facts are generated into `600s.asset-receipt.json` by
`scripts/write_600s_receipt.py`. Browser and visual-review evidence in that
file is recorded separately and is never auto-accepted. The template remains
the schema for future asset revisions. Cache identity lives in
`600s.version.js`. The authored Blender source is
`source/blender/600s-showcase-v1.1.blend`. The exact authored target is recorded in
`600s.configuration.json`.

Do not commit manufacturer BIM, commercial reference meshes, proprietary CAD, or any source asset whose license does not explicitly allow modification and public redistribution.

Recommended future layout:

```text
models/
├── 600s.glb
├── 600aj.glb
└── es1930m.glb
```

Keep authored Blender sources outside the deployable web directory or in a clearly separated `source/` directory with their own provenance record.
