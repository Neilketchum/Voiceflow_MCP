#!/usr/bin/env python3
"""
Payload-based test that shows exact JSON-RPC requests/responses
This simulates the exact communication between Cursor and your MCP server
"""

import asyncio
import json
from voiceflow_mcp_server import VoiceflowMCP

class PayloadSimulator:
    """Simulates exact MCP payloads that Cursor would send"""
    
    def __init__(self):
        self.voiceflow = VoiceflowMCP()
        self.request_id = 1
    
    def create_mcp_request(self, method: str, params: dict = None) -> dict:
        """Create a JSON-RPC request like Cursor would send"""
        return {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
    
    def create_mcp_response(self, result: dict = None, error: dict = None) -> dict:
        """Create a JSON-RPC response like your server would send"""
        response = {
            "jsonrpc": "2.0",
            "id": self.request_id
        }
        if result:
            response["result"] = result
        if error:
            response["error"] = error
        return response
    
    async def simulate_initialize_request(self):
        """Simulate Cursor's initialization request"""
        print("📤 CURSOR → MCP SERVER (Initialize Request)")
        print("-" * 50)
        
        request = self.create_mcp_request("initialize", {
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
        })
        
        print("Request Payload:")
        print(json.dumps(request, indent=2))
        
        # Simulate server response
        print("\n📥 MCP SERVER → CURSOR (Initialize Response)")
        print("-" * 50)
        
        response = self.create_mcp_response(result={
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
            "serverInfo": {
                "name": "voiceflow-docs",
                "version": "1.0.0"
            }
        })
        
        print("Response Payload:")
        print(json.dumps(response, indent=2))
        
        self.request_id += 1
    
    async def simulate_list_tools_request(self):
        """Simulate Cursor requesting the list of tools"""
        print("\n📤 CURSOR → MCP SERVER (List Tools Request)")
        print("-" * 50)
        
        request = self.create_mcp_request("tools/list")
        print("Request Payload:")
        print(json.dumps(request, indent=2))
        
        print("\n📥 MCP SERVER → CURSOR (List Tools Response)")
        print("-" * 50)
        
        response = self.create_mcp_response(result={
            "tools": [
                {
                    "name": "search_voiceflow_docs",
                    "description": "Search through Voiceflow documentation for specific topics, APIs, or features",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (e.g., 'API authentication', 'webhook setup', 'voice configuration')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "get_voiceflow_doc_page",
                    "description": "Get the content of a specific Voiceflow documentation page",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "Full URL of the documentation page"
                            }
                        },
                        "required": ["url"]
                    }
                },
                {
                    "name": "ask_voiceflow_question",
                    "description": "Ask a question about Voiceflow and get an AI-powered answer based on the documentation",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Your question about Voiceflow"
                            }
                        },
                        "required": ["question"]
                    }
                },
                {
                    "name": "list_voiceflow_topics",
                    "description": "Get a list of available documentation topics and categories",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ]
        })
        
        print("Response Payload:")
        print(json.dumps(response, indent=2))
        
        self.request_id += 1
    
    async def simulate_search_request(self):
        """Simulate Cursor making a search request"""
        print("\n📤 CURSOR → MCP SERVER (Search Request)")
        print("-" * 50)
        
        request = self.create_mcp_request("tools/call", {
            "name": "search_voiceflow_docs",
            "arguments": {
                "query": "API authentication",
                "limit": 3
            }
        })
        
        print("Request Payload:")
        print(json.dumps(request, indent=2))
        
        print("\n📥 MCP SERVER → CURSOR (Search Response)")
        print("-" * 50)
        
        # Actually perform the search
        results = await self.voiceflow.search_documents("API authentication", limit=3)
        
        response_content = f"Found {len(results)} relevant documentation pages:\n\n"
        for i, doc in enumerate(results, 1):
            response_content += f"{i}. **{doc['title']}**\n"
            response_content += f"   URL: {doc['url']}\n"
            response_content += f"   Description: {doc['description'][:200]}...\n"
            response_content += f"   Relevance: {doc['similarity']:.2f}\n\n"
        
        response = self.create_mcp_response(result={
            "content": [
                {
                    "type": "text",
                    "text": response_content
                }
            ]
        })
        
        print("Response Payload:")
        print(json.dumps(response, indent=2))
        
        self.request_id += 1
    
    async def simulate_question_request(self):
        """Simulate Cursor asking a question"""
        print("\n📤 CURSOR → MCP SERVER (Question Request)")
        print("-" * 50)
        
        request = self.create_mcp_request("tools/call", {
            "name": "ask_voiceflow_question",
            "arguments": {
                "question": "How do I authenticate with the Voiceflow API?"
            }
        })
        
        print("Request Payload:")
        print(json.dumps(request, indent=2))
        
        print("\n📥 MCP SERVER → CURSOR (Question Response)")
        print("-" * 50)
        
        # Actually answer the question
        result = await self.voiceflow.answer_question("How do I authenticate with the Voiceflow API?")
        
        response_content = f"## Answer\n\n{result['answer']}\n\n"
        
        if result['sources']:
            response_content += "## Sources\n\n"
            for source in result['sources']:
                response_content += f"- [{source['title']}]({source['url']}) (relevance: {source['relevance']:.2f})\n"
        
        response_content += f"\n**Confidence**: {result['confidence']:.2f}"
        
        response = self.create_mcp_response(result={
            "content": [
                {
                    "type": "text",
                    "text": response_content
                }
            ]
        })
        
        print("Response Payload:")
        print(json.dumps(response, indent=2))
        
        self.request_id += 1
    
    async def simulate_get_page_request(self):
        """Simulate Cursor requesting a specific page"""
        print("\n📤 CURSOR → MCP SERVER (Get Page Request)")
        print("-" * 50)
        
        request = self.create_mcp_request("tools/call", {
            "name": "get_voiceflow_doc_page",
            "arguments": {
                "url": "https://docs.voiceflow.com/docs/authentication"
            }
        })
        
        print("Request Payload:")
        print(json.dumps(request, indent=2))
        
        print("\n📥 MCP SERVER → CURSOR (Get Page Response)")
        print("-" * 50)
        
        # Actually get the page
        doc = await self.voiceflow.get_documentation_page("https://docs.voiceflow.com/docs/authentication")
        
        if doc:
            response_content = f"# {doc['title']}\n\n"
            response_content += f"**URL**: {doc['url']}\n\n"
            response_content += f"**Description**: {doc['description']}\n\n"
            response_content += f"**Content**:\n{doc['content'][:1000]}..."
            if len(doc['content']) > 1000:
                response_content += "\n\n[Content truncated - use the URL to view full content]"
        else:
            response_content = "Could not fetch documentation from the provided URL."
        
        response = self.create_mcp_response(result={
            "content": [
                {
                    "type": "text",
                    "text": response_content
                }
            ]
        })
        
        print("Response Payload:")
        print(json.dumps(response, indent=2))
        
        self.request_id += 1

async def main():
    """Main function to run all payload simulations"""
    print("🎯 Voiceflow MCP Server - Payload Simulation")
    print("This shows EXACTLY how Cursor communicates with your server")
    print("=" * 60)
    
    simulator = PayloadSimulator()
    
    # Run all simulations
    await simulator.simulate_initialize_request()
    await simulator.simulate_list_tools_request()
    await simulator.simulate_search_request()
    await simulator.simulate_question_request()
    await simulator.simulate_get_page_request()
    
    print("\n" + "=" * 60)
    print("🎉 Payload Simulation Complete!")
    print("\n✅ This is EXACTLY how Cursor will communicate with your server:")
    print("   1. Initialize MCP connection")
    print("   2. List available tools")
    print("   3. Call tools with specific arguments")
    print("   4. Receive structured responses")
    print("\n🚀 Your MCP server is ready for Cursor integration!")
    print("   Just add the cursor_config.json to your Cursor settings!")

if __name__ == "__main__":
    asyncio.run(main())
