# Official Blender MCP

This project uses Blender Labs' first-party Blender MCP 1.0.0 from
`https://projects.blender.org/lab/blender_mcp`, installed from source commit
`4309a39646e644261624bfcd2bca669b343b7621`.

## Installed layout

- Blender: `/Applications/Blender.app` (5.1.1 at setup time)
- Blender extension: `~/Library/Application Support/Blender/5.1/extensions/user_default/mcp`
- Isolated server: `<project>/.blender-mcp/venv/bin/blender-mcp`
- Source checkout and built extension: `<project>/tools/blender_mcp_official`
- Codex MCP name: `blender_official`
- Bridge: `localhost:9876` (observed as `127.0.0.1:9876`)

The local environment and source checkout are intentionally git-ignored. The
official server currently needs MCP SDK 1.x; this installation pins `mcp==1.29.1`
because MCP SDK 2.x removed the `mcp.server.fastmcp` API used by Blender MCP 1.0.0.
The reproducible package inputs are recorded in
`tools/blender-mcp-requirements.txt`.

## Start or reconnect

1. Start Blender normally with online access enabled. The MCP extension is
   enabled and its **Auto Start** setting defaults to on.
2. Confirm the bridge is local-only:

   ```sh
   lsof -nP -iTCP:9876 -sTCP:LISTEN
   ```

   The listener must be `127.0.0.1:9876` or `localhost:9876`, never a LAN address
   or `*:9876`.
3. Start a new Codex task in this repository after configuration changes. Codex
   Desktop and CLI share `~/.codex/config.toml`, so there is one MCP entry.
4. Run the bounded validation when needed:

   ```sh
   .blender-mcp/venv/bin/python scripts/validate_blender_mcp.py
   ```

The validation queries the active scene, creates only
`MCP_VALIDATION_CUBE`, verifies its 1 m x 1 m x 1 m dimensions and transform,
then deletes it. It refuses to overwrite an object with that name.

## Troubleshooting

### Blender MCP is not running

- Open **Edit > Preferences > Extensions > Installed > MCP**.
- Confirm the extension is enabled, Host is `localhost`, Port is `9876`, and
  **Auto Start** is enabled.
- Enable Blender's **Online Access** preference if Blender reports that it is
  required, then click **Start MCP Bridge Server** or restart Blender.

### Codex cannot see the server

- Run `codex mcp get blender_official` and confirm it is enabled.
- Restart the Codex task after adding or changing an MCP entry; a running task
  does not necessarily reload its MCP tool catalog.
- Confirm the executable exists at `<project>/.blender-mcp/venv/bin/blender-mcp`.

### Port 9876 is occupied

- Identify the listener with `lsof -nP -iTCP:9876 -sTCP:LISTEN`.
- Do not kill an unknown process. Either stop the known conflicting service or
  choose one unused high port in both Blender's MCP preferences and the
  `BLENDER_MCP_PORT` value in the Codex entry.
- Keep the Host set to `localhost`.

### The extension is disabled

- Re-enable **MCP** in Blender's installed extensions. If it is missing, rebuild
  and install the official checkout with Blender's `extension build` and
  `extension install-file --repo user_default --enable` commands.

### Reconnect after restarting Blender

- Blender's add-on bridge disappears when Blender exits. Start Blender again,
  wait for Auto Start, confirm the local listener, and retry the Codex tool call.
  The stdio MCP process can be relaunched by Codex; the Blender-side bridge must
  be running separately.

## Safety boundary

The official add-on executes model-generated Python without a security guard.
Use it only from this project workspace, do not open unrelated production files
during experiments, and keep the bridge local-only. No Poly Haven, Sketchfab,
cloud generation, telemetry add-ons, or other external 3D integrations were
installed or enabled as part of this setup. MCP readiness is not permission to
modify production geometry: the next gate is a controlled capability test
against `docs/MODEL_CONTRACT.md` and the dimensional research.
