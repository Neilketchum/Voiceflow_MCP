#!/usr/bin/env python3
"""
Test script for the Voiceflow MCP Server
"""

import asyncio
import json
from voiceflow_mcp_server import VoiceflowMCP

async def test_server():
    """Test the MCP server functionality"""
    print("🚀 Testing Voiceflow MCP Server...")
    
    # Initialize the server
    voiceflow = VoiceflowMCP()
    
    # Test 1: Fetch sitemap
    print("\n📋 Testing sitemap fetching...")
    urls = await voiceflow.fetch_sitemap()
    print(f"✅ Found {len(urls)} URLs in sitemap")
    
    # Test 2: Fetch a specific page
    print("\n📄 Testing document fetching...")
    test_url = "https://docs.voiceflow.com/docs/authentication"
    doc = await voiceflow.fetch_markdown_content(test_url)
    if doc:
        print(f"✅ Successfully fetched: {doc['title']}")
        print(f"   Description: {doc['description'][:100]}...")
    else:
        print("❌ Failed to fetch document")
    
    # Test 3: Search functionality
    print("\n🔍 Testing search functionality...")
    search_results = await voiceflow.search_documents("API authentication", limit=3)
    print(f"✅ Found {len(search_results)} search results")
    for i, result in enumerate(search_results, 1):
        print(f"   {i}. {result['title']} (relevance: {result['similarity']:.2f})")
    
    # Test 4: Q&A functionality
    print("\n🤖 Testing Q&A functionality...")
    qa_result = await voiceflow.answer_question("How do I authenticate with the Voiceflow API?")
    print(f"✅ Q&A result confidence: {qa_result['confidence']:.2f}")
    print(f"   Answer preview: {qa_result['answer'][:200]}...")
    print(f"   Sources: {len(qa_result['sources'])} documents")
    
    print("\n🎉 All tests completed!")

async def test_tools():
    """Test the MCP tools directly"""
    print("\n🛠️ Testing MCP Tools...")
    
    voiceflow = VoiceflowMCP()
    
    # Simulate tool calls
    tools_data = [
        {
            "name": "search_voiceflow_docs",
            "args": {"query": "webhook setup", "limit": 3}
        },
        {
            "name": "ask_voiceflow_question", 
            "args": {"question": "What are the main features of Voiceflow?"}
        },
        {
            "name": "list_voiceflow_topics",
            "args": {}
        }
    ]
    
    for tool_data in tools_data:
        print(f"\n🔧 Testing tool: {tool_data['name']}")
        try:
            if tool_data['name'] == "search_voiceflow_docs":
                results = await voiceflow.search_documents(
                    tool_data['args']['query'], 
                    tool_data['args']['limit']
                )
                print(f"   ✅ Found {len(results)} results")
                
            elif tool_data['name'] == "ask_voiceflow_question":
                result = await voiceflow.answer_question(tool_data['args']['question'])
                print(f"   ✅ Answer confidence: {result['confidence']:.2f}")
                
            elif tool_data['name'] == "list_voiceflow_topics":
                urls = await voiceflow.fetch_sitemap()
                categories = {}
                for url in urls:
                    path = url.split('/')[-2] if len(url.split('/')) > 1 else 'general'
                    categories[path] = categories.get(path, 0) + 1
                print(f"   ✅ Found {len(categories)} topic categories")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Voiceflow MCP Server Test Suite")
    print("=" * 50)
    
    # Run tests
    asyncio.run(test_server())
    asyncio.run(test_tools())
    
    print("\n✨ Test suite completed!")
    print("\nTo run the MCP server:")
    print("python voiceflow_mcp_server.py")
