#!/usr/bin/env python3
"""Execute one project-local Python file in Blender through the official MCP."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER = PROJECT_ROOT / ".blender-mcp" / "venv" / "bin" / "blender-mcp"


def decode_result(call_result: Any) -> dict[str, Any]:
    if call_result.isError:
        raise RuntimeError(repr(call_result.content))
    payload = json.loads(call_result.content[0].text)
    if not isinstance(payload, dict):
        raise RuntimeError("Expected an object response from Blender MCP")
    return payload


async def execute(script_path: Path) -> None:
    resolved = script_path.resolve()
    if PROJECT_ROOT not in resolved.parents:
        raise ValueError("The Blender script must be inside the JLG project")
    if not resolved.is_file():
        raise FileNotFoundError(resolved)

    env = os.environ.copy()
    env["BLENDER_MCP_HOST"] = "localhost"
    env["BLENDER_MCP_PORT"] = "9876"
    params = StdioServerParameters(command=str(SERVER), env=env)
    code = (
        "from pathlib import Path\n"
        f"_jlg_script = Path({str(resolved)!r})\n"
        "exec(compile(_jlg_script.read_text(encoding='utf-8'), str(_jlg_script), 'exec'), globals())\n"
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            response = decode_result(
                await session.call_tool("execute_blender_code", {"code": code})
            )
            if response.get("status") != "ok":
                raise RuntimeError(response.get("message", repr(response)))
            print(json.dumps(response, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("script", type=Path)
    args = parser.parse_args()
    asyncio.run(execute(args.script))


if __name__ == "__main__":
    main()
