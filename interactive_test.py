#!/usr/bin/env python3
"""
Interactive test for the Voiceflow MCP Server
Allows you to manually test each tool like Cursor would
"""

import asyncio
import json
import subprocess
import sys

class InteractiveMCPTester:
    """Interactive tester for MCP server"""
    
    def __init__(self):
        self.process = None
        self.request_id = 1
    
    async def start_server(self):
        """Start the MCP server"""
        print("🚀 Starting Voiceflow MCP Server...")
        self.process = subprocess.Popen(
            [sys.executable, "voiceflow_mcp_server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        await asyncio.sleep(2)
        print("✅ Server started!")
    
    def send_request(self, method: str, params: dict = None):
        """Send a request to the server"""
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str)
        self.process.stdin.flush()
        self.request_id += 1
    
    async def read_response(self):
        """Read response from server"""
        try:
            response_line = await asyncio.to_thread(self.process.stdout.readline)
            if response_line.strip():
                return json.loads(response_line.strip())
        except Exception as e:
            return {"error": str(e)}
        return {"error": "No response"}
    
    async def initialize(self):
        """Initialize the MCP connection"""
        print("\n🔧 Initializing MCP connection...")
        self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "interactive-test", "version": "1.0.0"}
        })
        
        response = await self.read_response()
        if "result" in response:
            print("✅ Initialization successful!")
            return True
        else:
            print(f"❌ Initialization failed: {response}")
            return False
    
    async def test_tool(self, tool_name: str, arguments: dict):
        """Test a specific tool"""
        print(f"\n🛠️ Testing {tool_name}...")
        print(f"   Arguments: {arguments}")
        
        self.send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        response = await self.read_response()
        
        if "result" in response and "content" in response["result"]:
            content = response["result"]["content"][0]["text"]
            print("✅ Success!")
            print("📄 Response:")
            print("-" * 50)
            print(content)
            print("-" * 50)
            return True
        else:
            print(f"❌ Failed: {response}")
            return False
    
    async def interactive_menu(self):
        """Interactive menu for testing"""
        while True:
            print("\n" + "=" * 60)
            print("🧪 Voiceflow MCP Server - Interactive Test")
            print("=" * 60)
            print("1. Search Documentation")
            print("2. Get Documentation Page")
            print("3. Ask Question")
            print("4. List Topics")
            print("5. List Available Tools")
            print("0. Exit")
            print("-" * 60)
            
            choice = input("Choose an option (0-5): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                query = input("Enter search query: ").strip()
                limit = input("Enter limit (default 5): ").strip() or "5"
                await self.test_tool("search_voiceflow_docs", {
                    "query": query,
                    "limit": int(limit)
                })
            elif choice == "2":
                url = input("Enter documentation URL: ").strip()
                if not url.startswith("https://docs.voiceflow.com/"):
                    url = f"https://docs.voiceflow.com/docs/{url}"
                await self.test_tool("get_voiceflow_doc_page", {"url": url})
            elif choice == "3":
                question = input("Enter your question: ").strip()
                await self.test_tool("ask_voiceflow_question", {"question": question})
            elif choice == "4":
                await self.test_tool("list_voiceflow_topics", {})
            elif choice == "5":
                print("\n🛠️ Listing available tools...")
                self.send_request("tools/list")
                response = await self.read_response()
                if "result" in response and "tools" in response["result"]:
                    tools = response["result"]["tools"]
                    print(f"✅ Found {len(tools)} tools:")
                    for tool in tools:
                        print(f"   • {tool['name']}: {tool['description']}")
                else:
                    print(f"❌ Failed to list tools: {response}")
            else:
                print("❌ Invalid choice. Please try again.")
    
    def cleanup(self):
        """Clean up"""
        if self.process:
            self.process.terminate()
            self.process.wait()

async def main():
    """Main function"""
    tester = InteractiveMCPTester()
    
    try:
        await tester.start_server()
        
        if await tester.initialize():
            await tester.interactive_menu()
        else:
            print("❌ Could not initialize MCP connection")
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
