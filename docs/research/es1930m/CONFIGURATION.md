# ES1930M Frozen Configuration

## Identity

- Model: JLG ES1930M
- Family: Micro-Sized Series
- Market and language: ANSI/United States, en-US
- Primary publication vintage code: PVC 2404
- Configuration ID: `ES1930M-PVC2404-US-STD-FR-FLA130-NM`

This is the standard current-production machine represented by JLG's PVC 2404 parts, service, and operation publications. It is not a generic 1930-class scissor lift and it is not an attempt to merge every ES1930M option into one machine.

## Included hardware

- Standard 52.8 x 27.6 in platform with 21.6 in extension deck
- Standard fixed rails and gate
- Five-level scissor stack
- Single-acting hydraulic lift cylinder with kicker-arm actuation
- Two-wheel electric drive on the hydraulic front-steer spindle assemblies
- Active pothole protection
- Two 12 V, 130 Ah flooded lead-acid batteries
- 10 x 3 in non-marking tires
- Leak containment system where shown by the frozen standard product configuration
- Ground and platform controls appropriate to the current ANSI machine

## Excluded hardware

The following variants are intentionally excluded from the base GLB and must not appear unless later introduced as separately evidenced option layers:

- Integrated mid-rail deck
- HVAC and ceiling-tile configurations
- Fold-down rails
- AGM or lithium-ion battery configurations
- Perimeter lighting
- AC inverter
- Hostile-environment package

## Published envelope

The frozen dimensions are 1.48 m long with the extension retracted, 2.03 m long with it deployed, 0.76 m wide, and 1.98 m high stowed. Wheelbase is 1.07 m. The standard platform is 1.34 x 0.70 m and travels 0.55 m. Indoor platform height is 5.64 m; outdoor height is limited to 4.57 m. Nominal mass is 1351 kg.

The current PVC 2404 material's 1.48 m / 58.2 in retracted length supersedes the 57.8 in value in older launch-era material for this reconstruction. The discrepancy remains recorded in `SOURCE_RECONCILIATION.md`; values are not silently averaged.

## Configuration discipline

Every modeled item is classified as one of:

- `verified`: directly supported by the frozen publication set;
- `derived`: mathematically obtained from verified values;
- `reconstructed`: authored to satisfy verified topology and envelopes where JLG publishes no fabrication coordinate;
- `deferred`: not represented as technical truth until better evidence exists.

Parts and service illustrations establish identity, adjacency, assembly order, and topology. They are not declared-to-scale fabrication drawings. The browser may communicate system function, but it must not imply that the model is a service procedure, load analysis, stability simulation, or safety authorization.

The machine-readable authority is `machines/es1930m/es1930m.configuration.json`. Its ID must be copied into the GLB metadata, asset receipt, and runtime machine adapter, and validators must fail on mismatch.
