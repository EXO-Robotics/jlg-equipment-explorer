# 600S reference-board manifest

Target: 8-12 high-value current-generation views. This directory intentionally contains no copied manufacturer images. Retrieve sources into an untracked local working board unless redistribution permission is established.

## Board slots

| Slot | Required view | Primary source | Location | Status | Modeling use |
|---:|---|---|---|---|---|
| 01 | clean elevated machine | R01 gallery asset 140381 | official silo PNG | reviewed | overall color split and elevated silhouette |
| 02 | elevated machine three-quarter | R02 | page 1, main product image | ready | boom, counterweight, chassis, platform relationship |
| 03 | top stowed | R02 | page 2, dimensions figure | ready | width, body plan, boom centerline, platform proportions |
| 04 | side stowed | R02 | page 2, dimensions figure | ready | 8.71 m envelope, wheelbase, boom rest angle, ground clearance |
| 05 | reach envelope | R02 | page 2, reach diagram | ready | visual-only elevation and extension poses |
| 06 | web range chart | R01 gallery asset 140382 | official range-chart JPG | reviewed | cross-check R02 chart presentation |
| 07 | rear three-quarter working view | R01 gallery asset 139098 | official teaser JPG | reviewed | turntable and chassis proportions in context |
| 08 | close rear three-quarter | R01 gallery asset 138896 | official teaser JPG | reviewed | tires, rear chassis, counterweight, and boom pivot |
| 09 | boom exploded diagram | R03 parts publication 3122579800 | exact page pending | blocked on manual capture | nesting, cylinder, pivot, and platform relationships |
| 10 | chassis/turntable exploded diagram | R03 parts publication 3122579800 | exact page pending | blocked on manual capture | slew center, enclosure, counterweight, axle placement |
| 11 | boom/pivot service diagram | R03 service publication 3122579700 | exact page pending | blocked on manual capture | hinge and cylinder-anchor understanding |
| 12 | current platform close-up | current JLG source preferred | source pending | evidence gap | rails, console, gate, and rotator silhouette |

## Board acceptance gate

Blender blockout may start when slots 01-08 are locally reviewed. Boom-pivot and detailed turntable work must wait for slots 09-11. Platform detail beyond its published 0.91 x 2.44 m envelope must wait for slot 12 or remain visibly simplified.

## Local board convention

Recommended untracked filenames:

```text
01_current-silo.png
02_spec-elevated.png
03_spec-top-stowed.png
04_spec-side-stowed.png
05_spec-reach-diagram.png
06_web-range-chart.jpg
07_current-detail.jpg
08_tire-detail.jpg
09_parts-boom.png
10_parts-chassis-turntable.png
11_service-boom-pivot.png
12_platform-closeup.png
```

For each local capture, record source ID, page or asset ID, retrieval date, and whether the image is current PVC 2607, current marketing material, or secondary comparison.

## Rights boundary

- Do not publish the assembled reference board.
- Do not commit JLG PDFs, manual-page captures, BIM files, dealer photography, or commercial-model renders without permission.
- Public repository documentation should retain links, publication identity, checksums, and written modeling decisions only.
