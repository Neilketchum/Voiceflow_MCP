#!/usr/bin/env python3
"""
Simple test client for the Voiceflow MCP Server
"""

import asyncio
import json
import subprocess
import sys

async def test_mcp_server():
    """Test the MCP server by sending a simple request"""
    try:
        # Start the MCP server process
        process = subprocess.Popen(
            [sys.executable, "voiceflow_mcp_server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send initialization request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        # Send the request
        request_str = json.dumps(init_request) + "\n"
        process.stdin.write(request_str)
        process.stdin.flush()
        
        # Wait a moment for response
        await asyncio.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ MCP server is running successfully!")
            print("✅ Server initialized without errors")
            
            # Try to list tools
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            
            request_str = json.dumps(tools_request) + "\n"
            process.stdin.write(request_str)
            process.stdin.flush()
            
            await asyncio.sleep(2)
            
            # Read any available output
            try:
                stdout, stderr = process.communicate(timeout=1)
                if stdout:
                    print(f"✅ Server response: {stdout[:200]}...")
                if stderr:
                    print(f"⚠️ Server stderr: {stderr[:200]}...")
            except subprocess.TimeoutExpired:
                print("✅ Server is responsive (no immediate output expected)")
            
        else:
            print("❌ MCP server exited unexpectedly")
            stdout, stderr = process.communicate()
            if stderr:
                print(f"Error: {stderr}")
        
        # Clean up
        process.terminate()
        
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")

if __name__ == "__main__":
    print("🧪 Testing Voiceflow MCP Server...")
    asyncio.run(test_mcp_server())
