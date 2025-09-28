#!/usr/bin/env python3
"""
Test script that simulates how Cursor would interact with the Voiceflow MCP Server
This tests the actual MCP protocol communication
"""

import asyncio
import json
import subprocess
import sys
import time
from typing import Dict, Any

class MCPClientSimulator:
    """Simulates how Cursor would communicate with the MCP server"""
    
    def __init__(self):
        self.process = None
        self.request_id = 1
    
    async def start_server(self):
        """Start the MCP server process"""
        self.process = subprocess.Popen(
            [sys.executable, "voiceflow_mcp_server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0  # Unbuffered
        )
        print("🚀 Started Voiceflow MCP Server")
        await asyncio.sleep(2)  # Give server time to initialize
    
    def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server"""
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        
        request_str = json.dumps(request) + "\n"
        print(f"📤 Sending: {method}")
        
        self.process.stdin.write(request_str)
        self.process.stdin.flush()
        
        self.request_id += 1
        return request
    
    async def read_response(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Read a JSON-RPC response from the MCP server"""
        try:
            # Read response with timeout
            response_line = await asyncio.wait_for(
                asyncio.to_thread(self.process.stdout.readline),
                timeout=timeout
            )
            
            if response_line.strip():
                response = json.loads(response_line.strip())
                print(f"📥 Received: {response.get('method', 'response')}")
                return response
            else:
                return {"error": "No response received"}
                
        except asyncio.TimeoutError:
            return {"error": "Response timeout"}
        except json.JSONDecodeError as e:
            return {"error": f"JSON decode error: {e}"}
        except Exception as e:
            return {"error": f"Read error: {e}"}
    
    async def test_initialization(self):
        """Test the initialization handshake (like Cursor would do)"""
        print("\n🔧 Testing MCP Initialization...")
        
        init_request = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": True
                },
                "resources": {
                    "subscribe": True,
                    "listChanged": True
                }
            },
            "clientInfo": {
                "name": "cursor",
                "version": "1.0.0"
            }
        }
        
        self.send_request("initialize", init_request)
        response = await self.read_response()
        
        if "result" in response:
            print("✅ Initialization successful!")
            print(f"   Server: {response['result'].get('serverInfo', {}).get('name', 'Unknown')}")
            print(f"   Protocol: {response['result'].get('protocolVersion', 'Unknown')}")
            return True
        else:
            print(f"❌ Initialization failed: {response}")
            return False
    
    async def test_list_tools(self):
        """Test listing available tools"""
        print("\n🛠️ Testing Tools List...")
        
        self.send_request("tools/list")
        response = await self.read_response()
        
        if "result" in response and "tools" in response["result"]:
            tools = response["result"]["tools"]
            print(f"✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"   • {tool['name']}: {tool['description'][:60]}...")
            return tools
        else:
            print(f"❌ Tools list failed: {response}")
            return []
    
    async def test_search_docs(self):
        """Test searching Voiceflow documentation"""
        print("\n🔍 Testing Document Search...")
        
        search_params = {
            "name": "search_voiceflow_docs",
            "arguments": {
                "query": "API authentication",
                "limit": 3
            }
        }
        
        self.send_request("tools/call", search_params)
        response = await self.read_response(timeout=10.0)
        
        if "result" in response and "content" in response["result"]:
            content = response["result"]["content"][0]["text"]
            print("✅ Search successful!")
            print(f"   Results: {content[:200]}...")
            return True
        else:
            print(f"❌ Search failed: {response}")
            return False
    
    async def test_get_doc_page(self):
        """Test getting a specific documentation page"""
        print("\n📄 Testing Document Retrieval...")
        
        get_params = {
            "name": "get_voiceflow_doc_page",
            "arguments": {
                "url": "https://docs.voiceflow.com/docs/authentication"
            }
        }
        
        self.send_request("tools/call", get_params)
        response = await self.read_response(timeout=10.0)
        
        if "result" in response and "content" in response["result"]:
            content = response["result"]["content"][0]["text"]
            print("✅ Document retrieval successful!")
            print(f"   Content: {content[:200]}...")
            return True
        else:
            print(f"❌ Document retrieval failed: {response}")
            return False
    
    async def test_ask_question(self):
        """Test asking a question about Voiceflow"""
        print("\n🤖 Testing Q&A...")
        
        qa_params = {
            "name": "ask_voiceflow_question",
            "arguments": {
                "question": "How do I authenticate with the Voiceflow API?"
            }
        }
        
        self.send_request("tools/call", qa_params)
        response = await self.read_response(timeout=10.0)
        
        if "result" in response and "content" in response["result"]:
            content = response["result"]["content"][0]["text"]
            print("✅ Q&A successful!")
            print(f"   Answer: {content[:200]}...")
            return True
        else:
            print(f"❌ Q&A failed: {response}")
            return False
    
    async def test_list_topics(self):
        """Test listing documentation topics"""
        print("\n📚 Testing Topics List...")
        
        topics_params = {
            "name": "list_voiceflow_topics",
            "arguments": {}
        }
        
        self.send_request("tools/call", topics_params)
        response = await self.read_response(timeout=10.0)
        
        if "result" in response and "content" in response["result"]:
            content = response["result"]["content"][0]["text"]
            print("✅ Topics list successful!")
            print(f"   Topics: {content[:200]}...")
            return True
        else:
            print(f"❌ Topics list failed: {response}")
            return False
    
    def cleanup(self):
        """Clean up the server process"""
        if self.process:
            self.process.terminate()
            self.process.wait()
            print("🧹 Cleaned up server process")

async def main():
    """Main test function"""
    print("🧪 Voiceflow MCP Server - Cursor Simulation Test")
    print("=" * 60)
    
    client = MCPClientSimulator()
    
    try:
        # Start the server
        await client.start_server()
        
        # Run all tests
        tests_passed = 0
        total_tests = 5
        
        # Test 1: Initialization
        if await client.test_initialization():
            tests_passed += 1
        
        # Test 2: List tools
        tools = await client.test_list_tools()
        if tools:
            tests_passed += 1
        
        # Test 3: Search docs
        if await client.test_search_docs():
            tests_passed += 1
        
        # Test 4: Get doc page
        if await client.test_get_doc_page():
            tests_passed += 1
        
        # Test 5: Ask question
        if await client.test_ask_question():
            tests_passed += 1
        
        # Test 6: List topics
        if await client.test_list_topics():
            tests_passed += 1
        
        # Results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            print("🎉 All tests passed! Your MCP server is ready for Cursor!")
        else:
            print("⚠️ Some tests failed. Check the errors above.")
        
        print("\n🚀 Your Voiceflow MCP Server is ready to use with Cursor!")
        print("   Configure Cursor using the cursor_config.json file")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
    
    finally:
        client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
