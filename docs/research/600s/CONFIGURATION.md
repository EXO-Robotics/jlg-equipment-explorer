# Frozen 600S reconstruction configuration

Freeze date: 2026-08-25  
Configuration ID: `600S-PVC2607-US-B3-2WS-D29-FF-RRP3696`

This is the one machine configuration the v1 reconstruction targets. It is a documented combination of current PVC 2607 assemblies, not a claim that every current 600S has these options and not a substitute for a real machine serial plate.

| Field | Frozen choice | Evidence and boundary |
|---|---|---|
| Model | standard 600S, not 600S HC3 or 660SJ | R01-R03 |
| Product variation | PVC 2607 | R03 current parts/service/operation set |
| Market | ANSI, United States, English | R02 standard sheet and R03 ANSI assembly families |
| Serial family | B3-family current assembly branch | R03 parts figures explicitly distinguish B3; no exact serial number is invented |
| Drive/steer | four-wheel hydrostatic drive, two-wheel steer | R02 lists 4WD as standard; R03 labels rear steer hardware `4WS ONLY`, so 2WS is the baseline branch |
| Engine | Deutz D2.9L4 Tier 4 Final, 48.8/49 hp | R02 standard engine listing; R03 49 hp D2.9 assembly family |
| Fuel tank | 31 gal / 117 L diesel configuration | R02 and operation publication 3122579600 p137 |
| Hoods | B3 DCPD exterior family where compatible with the chosen ANSI configuration | parts publication 3122579800 pp194-204; internal details remain hidden unless separately modeled |
| Tires | standard foam-filled 355/55D625 | R02 standard tire; operation publication p141; parts publication pp46-47 |
| Platform | 36 x 96 in / 0.91 x 2.44 m B3 rapid-replace platform with self-closing swing gate | R02 standard feature and envelope; parts publication pp654, 660, 666-668 |
| Capacity presentation | 600 lb unrestricted; 1,000 lb restricted | R02; operation publication p135 |
| Standard visible technology | CS550 LED motion/amber beacon, ClearSky hardware, SkyGuard SkyLine, USB-A/USB-C | R01/R02 standard features; only add when placement is supported |
| Optional equipment | omitted | no quad tracks, 4WS, generator/SkyPower, SkyWelder, SkyGlazier, Soft Touch, SkySense, hostile/arctic/cold-weather packages, turf/non-marking tires, tow package, fall-arrest accessory, or platform mesh |

## Modeling authority classes

- `verified`: published dimensions or an unambiguous current assembly identity.
- `derived`: a relationship calculated from verified values and recorded with its method.
- `reconstructed`: a visually matched shape or placement bounded by current official views but not dimensioned.
- `deferred`: hidden, simplified, or represented by an empty contract node because the evidence does not support the detail.

No manual diagram is a fabrication drawing. Fastener counts, hose routes, harness routes, cylinder anchors, and pivot offsets may be represented visually only when their placement is unambiguous at showcase scale. Safety behavior, load sensing, stability, hydraulic pressure, electrical diagnosis, and service procedures remain outside the simulation.
