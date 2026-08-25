# 600S reference register

Evidence freeze date: 2026-08-25

## Scope decision

The target is the current standard JLG 600S represented by the June/July 2026 public product material. The 600S HC3, legacy 600S generations, 600SJ, and 660SJ are separate configurations. They may explain shared mechanisms but must not silently supply current 600S geometry.

JLG uses a Product Variation Code (PVC) in its current publication catalog. The current parts, service, and operation set is listed under PVC 2607. The separately cataloged hydraulic and electrical schematic files are listed under PVC 2601 and remain quarantined. The inspected PVC 2607 service and parts manuals contain their own applicable hydraulic and electrical diagrams; those in-manual diagrams are authoritative within their stated model, market, steering, engine, and serial-family scope.

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
- Confidence: high for catalog metadata; all three PVC 2607 manuals were directly inspected on 2026-08-25

Current PVC 2607 English set listed on 2026-08-25:

| Type | Publication | Release date | Listed size | Content status |
|---|---:|---|---:|---|
| Parts | 3122579800 | 2026-07-13 | 91.68 MB | inspected; SHA-256 `6e0e8ae6fe3b5ce6d726c13945bb8c6fd006ed7183631a0c74044803306ea1fc` |
| Service | 3122579700 | 2026-07-13 | 119.82 MB | inspected; SHA-256 `2e74966adf93d7432c43647eccc02105f2a868f379d4a74c8b9a8d01e5a2c7b5` |
| Operation | 3122579600 | 2026-07-13 | 29.11 MB | inspected; SHA-256 `0a60dd1e8ed70d9a782f36f4ffbf5ca0260d3faedbd43f136cb0fe7f1d8a52c6` |

Directly inspected current-page anchors used by the reconstruction:

| Publication | Pages | Verified modeling use |
|---:|---:|---|
| 3122579600 | 28 | 600S nomenclature: base, mid, and fly boom; powertrack; rotator; leveling cylinder; controls |
| 3122579600 | 135-141 | capacity, 2WS/4WS weights, dimensions, engines, and standard tire data |
| 3122579800 | 20-64 | axle, steering, wheel-drive, tire/wheel, and frame-cover assemblies |
| 3122579800 | 70-242 | 600S turntable valves, slew, bearing, tanks, electrical components, controls, hoods, and covers |
| 3122579800 | 520, 540 | 600S boom installation and base-section assembly |
| 3122579800 | 568-612 | rotator, powertrack, boom valves/sensors, and 600S rapid-platform support |
| 3122579800 | 654-668 | B3 36 x 96 in rapid-replace platform, gate family, console, and footswitch |
| 3122579800 | 724-804 | axle, level, lift, steer, and telescope cylinders plus applicable hydraulic diagrams |
| 3122579800 | 898-1054 | boom sensors and current harness families |
| 3122579700 | 641 | base/mid/fly boom, powertrack, tower links, and platform rotator relationships |
| 3122579700 | 648 | main boom, tower-link, support-strap, and pivot-pin relationships |
| 3122579700 | 659 | 600S platform removal/installation relationship |
| 3122579700 | 973-1018 | in-manual electrical and hydraulic schematics for the covered PVC 2607 manual |

Current catalog entries that must remain quarantined from PVC 2607 geometry until applicability is confirmed:

| Type | Publication | PVC | Release date | Reason quarantined |
|---|---:|---:|---|---|
| Hydraulic schematic | 3122588600 | 2601 | 2026-01-12 | different PVC |
| Electrical schematic | 3122586300 | 2601 | 2026-01-12 | different PVC |
| Parts | 3122560500 | 2601 | 2026-06-01 | superseded/different PVC listing |
| Service | 3122560400 | 2601 | 2026-06-30 | different PVC |
| Operation | 3122560300 | 2601 | 2026-01-12 | different PVC |

Locally inspected, uncommitted standalone schematic identities:

| Type | Publication | Pages | Retrieved-file SHA-256 | Permitted use |
|---|---:|---:|---|---|
| Hydraulic | 3122588600 | 7 | `ba0101934d194ef2141945bc7f1c7703a1ac7915c1260a987e1e68e6ca42d18e` | provisional circuit and component taxonomy only |
| Electrical | 3122586300 | 13 | `4fffbb392e2adfb0ea9728e244d6e6106d103472b87c53c86ae77ac307e998ff` | provisional harness and system taxonomy only |

The hashes and authority rules are machine checked by `SOURCE_MANIFEST.json` and
`MECHANISM_EVIDENCE.json`. Signed catalog download URLs are intentionally excluded
from Git; they are transient delivery links, not stable source identifiers.

## Current mechanism corrections

- PVC 2607 parts pages 542-543 identify telescope cylinder `1001309294`, base
  weldment `1001176208`, mid weldment `1001176212`, and fly weldment
  `1001265639`, together with current extend/retract ropes and sheaves.
- Service pages 51-52 establish coupled rope behavior but do not publish an exact
  Mid-to-Fly transform ratio or current physical telescope stroke.
- Service pages 643-645 establish a folded powertrack carrier, push tube, support,
  wear pad, and mixed hydraulic/electrical contents. They do not establish a
  frozen-B3 link count, pitch, or deployed length.
- Parts pages 28-29 establish the no-tow 2WS topology: two steer cylinders
  (`1001181792`), one tie rod (`1001181793`), knuckles (`1001263271`), and
  kingpins. Anchor coordinates and stroke remain unresolved.
- Service pages 36 and 656-658 establish electronic starting-angle retention,
  the platform-angle sensor/pin relationship, and the leveling-cylinder/rotator
  linkage. This is not automatic leveling to gravity.

Two frequently repeated legacy claims are explicitly rejected as current-PVC
geometry authority: cylinder `1683618` with 18.8/32.8 ft lengths, and powertrack
`1001099832` with a 228 in/57-link description. Neither may drive the current
model without a new applicability record.

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

## Remaining source gates

1. Acquire current front, rear, underside, and engine-bay photographs from JLG material or record same-generation secondary sources with explicit lower confidence.
2. Do not use a serial-dependent assembly unless it matches the frozen B3 configuration in `CONFIGURATION.md` or is clearly recorded as a common-family reconstruction.
3. Keep standalone schematic publications 3122588600 and 3122586300 quarantined unless JLG confirms PVC 2607 applicability.
4. Treat manual exploded views as assembly-relationship evidence, not fabrication dimensions.
