#!/usr/bin/env python3
"""Run the bounded JLG Blender MCP connection check and restore the scene."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER = PROJECT_ROOT / ".blender-mcp" / "venv" / "bin" / "blender-mcp"
VALIDATION_OBJECT = "MCP_VALIDATION_CUBE"


def decode_result(call_result: Any) -> dict[str, Any]:
    if call_result.isError:
        raise RuntimeError(repr(call_result.content))
    payload = json.loads(call_result.content[0].text)
    if not isinstance(payload, dict):
        raise RuntimeError("Expected an object response from Blender MCP")
    return payload


async def main() -> None:
    env = os.environ.copy()
    env["BLENDER_MCP_HOST"] = "localhost"
    env["BLENDER_MCP_PORT"] = "9876"
    params = StdioServerParameters(command=str(SERVER), env=env)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            tool_names = {tool.name for tool in tools.tools}
            required = {"get_objects_summary", "execute_blender_code"}
            if not required.issubset(tool_names):
                raise RuntimeError(f"Missing required tools: {sorted(required - tool_names)}")

            scene_before = decode_result(await session.call_tool("get_objects_summary", {}))
            create_code = f'''
import bpy
name = {VALIDATION_OBJECT!r}
if bpy.data.objects.get(name) is not None:
    result = {{"created": False, "reason": "name collision"}}
else:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
    obj = bpy.context.active_object
    obj.name = name
    obj.dimensions = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()
    result = {{
        "created": True,
        "name": obj.name,
        "dimensions_m": list(obj.dimensions),
        "location_m": list(obj.location),
        "rotation_euler_rad": list(obj.rotation_euler),
        "scale": list(obj.scale),
    }}
'''
            query_code = f'''
import bpy
obj = bpy.data.objects.get({VALIDATION_OBJECT!r})
result = {{"exists": obj is not None}}
if obj is not None:
    result.update({{
        "name": obj.name,
        "dimensions_m": list(obj.dimensions),
        "location_m": list(obj.location),
        "rotation_euler_rad": list(obj.rotation_euler),
        "scale": list(obj.scale),
    }})
'''
            delete_code = f'''
import bpy
obj = bpy.data.objects.get({VALIDATION_OBJECT!r})
if obj is not None:
    bpy.data.objects.remove(obj, do_unlink=True)
result = {{"deleted": obj is not None, "exists_after": bpy.data.objects.get({VALIDATION_OBJECT!r}) is not None}}
'''

            created = False
            try:
                create_result = decode_result(
                    await session.call_tool("execute_blender_code", {"code": create_code})
                )
                created = bool(create_result.get("result", {}).get("created"))
                if not created:
                    raise RuntimeError(f"Validation object was not created: {create_result}")

                query_result = decode_result(
                    await session.call_tool("execute_blender_code", {"code": query_code})
                )
                observed = query_result.get("result", {})
                if observed.get("name") != VALIDATION_OBJECT:
                    raise RuntimeError(f"Unexpected validation object: {observed}")
                dimensions = observed.get("dimensions_m")
                if dimensions != [1.0, 1.0, 1.0]:
                    raise RuntimeError(f"Unexpected dimensions: {dimensions}")
            finally:
                if created:
                    delete_result = decode_result(
                        await session.call_tool("execute_blender_code", {"code": delete_code})
                    )
                    if delete_result.get("result", {}).get("exists_after"):
                        raise RuntimeError("Validation object cleanup failed")

            print(json.dumps({
                "status": "PASS",
                "server": initialized.serverInfo.name,
                "server_version": initialized.serverInfo.version,
                "tool_count": len(tool_names),
                "scene_query": "PASS" if scene_before else "PASS_EMPTY_RESPONSE",
                "object": observed,
                "cleanup": "PASS",
            }, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
