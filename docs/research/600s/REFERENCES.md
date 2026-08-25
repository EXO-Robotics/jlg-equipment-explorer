# 600S reference register

Evidence freeze date: 2026-08-25

## Scope decision

The target is the current standard JLG 600S represented by the June/July 2026 public product material. The 600S HC3, legacy 600S generations, 600SJ, and 660SJ are separate configurations. They may explain shared mechanisms but must not silently supply current 600S geometry.

JLG uses a Product Variation Code (PVC) in its current publication catalog. The current parts, service, and operation set is listed under PVC 2607. Current hydraulic and electrical schematics are listed under PVC 2601. Until JLG confirms cross-PVC applicability, those schematics are not authoritative for the PVC 2607 model.

## Primary sources

### R01 - Current JLG 600S product page

- Owner: JLG Industries, Inc.
- Title: 600S Telescopic Boom Lift
- URL: https://www.jlg.com/en/equipment/boom-lifts/telescopic/engine-powered/600-series/600s
- Page state: copyright 2026; live page inspected 2026-08-25
- Model applicability: current standard 600S product page
- Used for: current exterior presentation, gallery inventory, headline reach/capacity/height, axle oscillation, gradeability, and swing
- Confidence: high for the values visibly published on the page
- Caveat: page copy says capacity has increased to 600 lb while separately listing maximum capacity as 1,000 lb. The current spec sheet resolves this as 600 lb unrestricted and 1,000 lb restricted.

### R02 - Current JLG 600S specification sheet

- Owner: JLG Industries, Inc.
- Title: 600S Telescopic Boom Lift
- Stable JLG URL: https://www.jlg.com/dfsmedia/e4042b10c9ce4595b4cc059f1299f079/125485-source
- Part number: 3131050
- Revision: R0626_04
- PDF creation date: 2026-07-13 13:40:56 EDT
- Pages: 2
- Retrieved: 2026-08-25
- Retrieved-file SHA-256: `56123e6ef835a4c1caebc00ad26f2e1f02e16899a2bbe6e6f4bbd871ee8885b5`
- Used for: current published dimensions, performance values, platform size, tires, silhouette views, and reach diagram
- Confidence: high as a current manufacturer specification sheet
- Precision caveat: page 2 states that all dimensions are approximate.
- Repository policy: do not commit the PDF or extracted images without redistribution permission; retain the URL, identity, and checksum.

### R03 - Current JLG Online Express publication catalog

- Owner: JLG Industries, Inc.
- Title: Technical Publications
- Root URL: https://onlineexpress.jlg.com/technical-publications
- Model-filter URL: https://onlineexpress.jlg.com/technical-publications/search/english-united-states/model-600s/_/N-1063887702%2B1277404462?locale=en-us
- Catalog inspected: 2026-08-25
- Used for: publication identity, release date, language, model, PVC, file size, and manual-family selection
- Confidence: high for catalog metadata; manual contents remain pending direct inspection

Current PVC 2607 English set listed on 2026-08-25:

| Type | Publication | Release date | Listed size | Content status |
|---|---:|---|---:|---|
| Parts | 3122579800 | 2026-07-13 | 91.68 MB | download/page capture pending |
| Service | 3122579700 | 2026-07-13 | 119.82 MB | download/page capture pending |
| Operation | 3122579600 | 2026-07-13 | 29.11 MB | download/page capture pending |

Current catalog entries that must remain quarantined from PVC 2607 geometry until applicability is confirmed:

| Type | Publication | PVC | Release date | Reason quarantined |
|---|---:|---:|---|---|
| Hydraulic schematic | 3122588600 | 2601 | 2026-01-12 | different PVC |
| Electrical schematic | 3122586300 | 2601 | 2026-01-12 | different PVC |
| Parts | 3122560500 | 2601 | 2026-06-01 | superseded/different PVC listing |
| Service | 3122560400 | 2601 | 2026-06-30 | different PVC |
| Operation | 3122560300 | 2601 | 2026-01-12 | different PVC |

### R04 - Serial-bound legacy JLG operation manual

- Owner: JLG Industries, Inc.
- Title: Operation and Safety Manual, Boom Lift Models 600S and 660SJ
- URL: https://csapps.jlg.com/ifOnlineManuals/Manuals/JLG/JLG%20Boom%20Lifts/600S_600SJ_660SJ/Operation%20Manuals/SN%200300235168%20to%200300272445/3121727_H_600S%2C660SJ_JLG_Operation_English.pdf
- Publication: 3121727
- Revision/date: Rev H, 2021-01-19
- Serial applicability: S/N 0300235168 through 0300272445 and B300002655 through B300005754, subject to cover exceptions
- Used for: historical comparison and terminology only
- Confidence: high within its stated serial range
- Prohibited use: do not overwrite current R02 dimensions or infer current PVC 2607 geometry from this manual.

### R05 - Official JLG MEWP terminology

- Owner: JLG Industries, Inc.
- Title: Learn the Lingo: Common MEWP Terms
- URL: https://www.jlg.com/en/directaccess/learn-the-lingo-common-mewp-terms
- Inspected: 2026-08-25
- Used for: interpreting `tailswing` as the rear of the rotating turntable extending beyond an edge of the drive chassis
- Confidence: high for JLG terminology; R02 remains authoritative for the current 600S value

## Official gallery assets

These asset identifiers are linked by R01. Record them for reference-board retrieval; do not copy them into the public repository without permission.

| Asset ID | Product-page label | Current source form | Intended use |
|---:|---|---|---|
| 140381 | 800X600-600S-LFT-U-silo | `https://dam.jlg.com/DigizuiteCore/LegacyService/api/assetstream/140381/-1.png` | transparent elevated silhouette; inspected 2026-08-25 |
| 140382 | jlg-RangeChart-600S | `https://dam.jlg.com/DigizuiteCore/LegacyService/api/assetstream/140382/-1.jpg` | reach-envelope cross-check; inspected 2026-08-25 |
| 139098 | DATeaser-1000x600-600S | `https://dam.jlg.com/DigizuiteCore/LegacyService/api/assetstream/139098/-1.jpg` | in-situ rear three-quarter working view; inspected 2026-08-25 |
| 138896 | DATeaser_1000x600_600S-Tires | `https://dam.jlg.com/DigizuiteCore/LegacyService/api/assetstream/138896/-1.jpg` | close rear three-quarter chassis, counterweight, boom-pivot, and tire view; inspected 2026-08-25 |

## Secondary sources

No secondary source is admitted into the dimensional authority chain. Manufacturer-attributed BIM, rental photos, dealer photos, and commercial models may be logged later for visual comparison only. Each must identify generation/configuration and license before use.

## User-supplied comparison images

The following local images were visually inspected on 2026-08-25 but are not admitted as current-generation geometry evidence:

| Local filename | Resolution | Status | Permitted use |
|---|---:|---|---|
| `images.jpeg` | 638 x 480 | source, license, serial range, and generation unknown; appears legacy | broad orange/cream/dark material separation and silhouette comparison only |
| `images-2.jpeg` | 554 x 554 | source, license, serial range, and generation unknown; appears legacy | broad material and extended-pose comparison only |
| `images-3.jpeg` | 300 x 508 | source, license, serial range, and generation unknown; appears legacy | broad elevated-pose and tire-value comparison only |

Do not use these files to resolve current PVC 2607 enclosure profiles, pivots, cylinder anchors, telescope construction, platform details, or decals. Do not copy them into the public repository without source and redistribution permission.

## Unresolved source gates

1. Obtain direct, local working copies of publications 3122579800, 3122579700, and 3122579600 outside the deployable repository.
2. Record their checksums and inspect covers for exact applicability.
3. Capture only the specific boom, chassis/turntable, platform, and pivot pages required by the reference-board manifest.
4. Confirm whether schematics 3122588600 and 3122586300 apply to PVC 2607 before consulting them.
5. Acquire current front, rear, and platform close-ups from JLG material or record a same-generation secondary source with explicit lower confidence.
