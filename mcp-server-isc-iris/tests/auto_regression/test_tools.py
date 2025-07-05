#!/usr/bin/env python3
"""
Test script for MCP Server tools.

This script provides an interactive way to test the MCP server tools.
"""
import asyncio
import json
from typing import Dict, Any
from mcp_server_iris.example import MCPClient

async def list_tools():
    """List all available tools."""
    async with MCPClient() as client:
        tools = await client.list_tools()
        print("\nAvailable Tools:")
        for i, tool in enumerate(tools, 1):
            print(f"{i}. {tool.name} - {tool.description}")
        return tools

async def execute_tool(tool_name: str, params: Dict[str, Any]):
    """Execute a specific tool with the given parameters."""
    async with MCPClient() as client:
        try:
            result = await client.call_tool(tool_name, params)
            print(f"\nResult from {tool_name}:")
            print(json.dumps(result, indent=2, default=str))
            return result
        except Exception as e:
            print(f"Error executing {tool_name}: {e}")
            raise

async def interactive_mode():
    """Run in interactive mode to test tools."""
    tools = await list_tools()
    
    while True:
        try:
            print("\nEnter tool number to execute (or 'q' to quit): ", end="")
            choice = input().strip().lower()
            
            if choice == 'q':
                break
                
            try:
                tool_idx = int(choice) - 1
                if 0 <= tool_idx < len(tools):
                    tool = tools[tool_idx]
                    print(f"\nExecuting: {tool.name}")
                    print(f"Description: {tool.description}")
                    
                    # Get parameters
                    params = {}
                    for param in tool.parameters:
                        value = input(f"Enter {param.name} ({param.type}): ").strip()
                        # Convert to appropriate type
                        if param.type == "integer":
                            value = int(value)
                        elif param.type == "boolean":
                            value = value.lower() in ('true', 'yes', 'y', '1')
                        params[param.name] = value
                    
                    await execute_tool(tool.name, params)
                else:
                    print("Invalid tool number")
            except ValueError:
                print("Please enter a valid number")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(interactive_mode())
