# Equipment Explorer machine interface

The runtime must support multiple machines without weakening the frozen 600S contract. A machine module supplies identity and behavior; the shared viewer owns presentation infrastructure.

## Shared runtime responsibilities

- renderer, stage, lighting and render profiles;
- orbit camera, pointer/touch/keyboard input and idle motion;
- GLB loading, failure state and cache identity;
- selection/raycasting and moving interaction outlines;
- responsive controls, inspector shell and focus management;
- diagnostics, runtime error count, frame sampling and reduced motion;
- receipt/configuration validation dispatch.

## Machine module responsibilities

Each machine module exports immutable data and bounded behavior:

```js
{
  id,
  release,
  assetUrl,
  configurationId,
  identity,
  specifications,
  controls,
  components,
  cameras,
  requiredNodes,
  interactionVolumes,
  validateAsset(root),
  createRig(root),
  applyState(rig, state, delta),
  stowState,
  defaultCamera
}
```

The shared runtime must not contain model names, configuration IDs, machine-specific node names, motion ranges, inspector prose or focus poses.

## Compatibility sequence

1. Define the interface alongside the existing implementation.
2. Wrap the current 600S constants and behavior without renaming its GLB nodes or changing its receipt.
3. Prove the exact current 600S GLB and viewer acceptance checks still pass.
4. Add ES1930M as the first native second-machine module.
5. Add route and equipment selection only after both modules pass direct URLs independently.

## URL contract

- `/jlg-equipment-explorer/600s/`
- `/jlg-equipment-explorer/es1930m/`
- `/jlg-equipment-explorer/` becomes equipment selection only after machine routes are stable.

Legacy root behavior must remain available through a redirect or compatible default until the deployed 600S URL transition is explicitly approved.

## Machine-specific acceptance

The common runtime may report that a module loaded and its declared controls/components resolved. Only the machine-specific validator can claim mechanical closure. For ES1930M, a generic node-presence test cannot replace sampled linkage, slide, cylinder and continuity checks.
