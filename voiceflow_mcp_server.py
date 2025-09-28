#!/usr/bin/env python3
"""
Voiceflow Documentation MCP Server

This MCP server provides AI-aided development support for Voiceflow by:
1. Searching through Voiceflow documentation
2. Fetching specific documentation pages
3. Answering questions about Voiceflow features and APIs
4. Providing code examples and integration guidance

Perfect for Cursor AI development assistance!
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentCache:
    """Simple in-memory cache for documentation content"""
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.embeddings: Optional[np.ndarray] = None
        self.documents: List[Dict[str, Any]] = []
    
    def get(self, url: str) -> Optional[Dict[str, Any]]:
        return self.cache.get(url)
    
    def set(self, url: str, content: Dict[str, Any]) -> None:
        self.cache[url] = content
    
    def has_embeddings(self) -> bool:
        return self.embeddings is not None and len(self.documents) > 0

class VoiceflowMCP:
    def __init__(self):
        self.base_url = "https://docs.voiceflow.com"
        self.sitemap_url = "https://docs.voiceflow.com/sitemap.xml"
        self.cache = DocumentCache()
        self.embedding_model = None
        self.http_client = httpx.AsyncClient(
            timeout=30.0, 
            headers={"User-Agent": "voiceflow-mcp/1.0 (+https://github.com/voiceflow/mcp-server)"}
        )
        
        # Initialize embedding model for semantic search
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Loaded embedding model for semantic search")
        except Exception as e:
            logger.warning(f"Could not load embedding model: {e}")
    
    async def fetch_sitemap(self) -> List[str]:
        """Fetch and parse the sitemap to get all documentation URLs"""
        try:
            response = await self.http_client.get(self.sitemap_url)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            urls = []
            
            # Parse XML sitemap
            for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc_elem is not None and loc_elem.text:
                    urls.append(loc_elem.text)
            
            logger.info(f"Found {len(urls)} URLs in sitemap")
            return urls
            
        except Exception as e:
            logger.error(f"Error fetching sitemap: {e}")
            return []
    
    async def fetch_markdown_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch markdown content from a Voiceflow documentation URL"""
        cached = self.cache.get(url)
        if cached:
            return cached

        async def _get(u: str) -> Optional[httpx.Response]:
            headers = {"Accept": "text/markdown, text/plain, */*"}
            for attempt in range(4):
                r = await self.http_client.get(u, headers=headers, follow_redirects=True)
                if r.status_code == 429 or 500 <= r.status_code < 600:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                if r.is_success:
                    return r
                break
            return None

        md_url = url if url.endswith(".md") else f"{url}.md"

        # 1) Try .md
        r = await _get(md_url)
        body = None
        final_url = md_url
        if r is not None:
            ctype = (r.headers.get("content-type") or "").lower()
            body = r.text
            # accept markdown-ish even if served as text/plain
            if ("markdown" in ctype) or ("text/plain" in ctype) or body.startswith("# ") or "```" in body:
                pass
            else:
                body = None

        # 2) Fallback to original URL
        if body is None:
            r2 = await _get(url)
            if r2 is not None and r2.is_success:
                ctype = (r2.headers.get("content-type") or "").lower()
                text2 = r2.text
                # some endpoints serve raw md with text/plain
                if ("markdown" in ctype) or ("text/plain" in ctype) or text2.startswith("# ") or "```" in text2:
                    body = text2
                    final_url = url

        if body is None:
            logger.warning(f"No markdown found for {url}")
            return None

        title = self.extract_title(body)
        description = self.extract_description(body)
        cleaned = self.clean_markdown(body)
        
        # Create chunks for better search
        chunks = self.chunk_markdown(cleaned)

        doc_data = {
            "url": url,                # canonical
            "markdown_url": final_url, # where we fetched md
            "title": title,
            "description": description,
            "content": cleaned,
            "raw_content": body,
            "chunks": chunks
        }
        self.cache.set(url, doc_data)
        logger.info(f"Fetched (MD): {title} — {final_url}")
        return doc_data
    
    def extract_title(self, content: str) -> str:
        """Extract title from markdown content"""
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            if line.startswith('# '):
                return line[2:].strip()
            elif line.startswith('title:'):
                return line[6:].strip()
        return "Untitled"
    
    def extract_description(self, content: str) -> str:
        """Extract description from markdown content"""
        lines = content.split('\n')
        for i, line in enumerate(lines[:20]):  # Check first 20 lines
            if line.startswith('description:'):
                return line[12:].strip()
            elif line.startswith('## ') and i > 0:
                # Use the first paragraph after title as description
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip() and not lines[j].startswith('#'):
                        return lines[j].strip()[:200] + "..."
        return ""
    
    def clean_markdown(self, content: str) -> str:
        """Clean markdown content for better processing"""
        # Remove frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2]
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        return content.strip()
    
    def chunk_markdown(self, md: str) -> List[Dict[str, Any]]:
        """Chunk markdown by headings for better search granularity"""
        chunks = []
        lines = md.splitlines()
        buf, current_h = [], None
        in_code = False

        def flush():
            if not buf: return
            text = "\n".join(buf).strip()
            if text:
                chunks.append({"heading": current_h or "", "markdown": text})
            buf.clear()

        for ln in lines:
            if ln.strip().startswith("```"):
                in_code = not in_code
                buf.append(ln)
                continue
            if not in_code and re.match(r"^#{1,3}\s", ln):
                flush()
                current_h = re.sub(r"^#{1,3}\s+", "", ln).strip()
                buf.append(ln)
            else:
                buf.append(ln)
        flush()
        return chunks
    
    async def search_documents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search through cached documents using semantic similarity"""
        if not self.cache.has_embeddings():
            await self.build_embeddings()
        if not self.embedding_model or not self.cache.has_embeddings():
            return await self.simple_search(query, limit)

        q = self.embedding_model.encode([query])
        sims = np.dot(self.cache.embeddings, q.T).flatten()
        idxs = np.argsort(sims)[::-1][:limit]

        results = []
        for i in idxs:
            doc = self.cache.documents[i]
            results.append({**doc, "similarity": float(sims[i])})
        return results
    
    async def simple_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Simple text-based search fallback"""
        query_lower = query.lower()
        results = []
        
        for url, doc_data in self.cache.cache.items():
            score = 0
            
            # Check title
            if query_lower in doc_data.get("title", "").lower():
                score += 3
            
            # Check description
            if query_lower in doc_data.get("description", "").lower():
                score += 2
            
            # Check content
            content_lower = doc_data.get("content", "").lower()
            if query_lower in content_lower:
                score += content_lower.count(query_lower)
            
            if score > 0:
                results.append({
                    **doc_data,
                    "similarity": score / 10.0  # Normalize score
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]
    
    async def build_embeddings(self) -> None:
        """Build embeddings for all cached documents using chunks"""
        if not self.embedding_model:
            return
        docs, texts = [], []
        for url, doc in self.cache.cache.items():
            for idx, ch in enumerate(doc.get("chunks", [])):
                # text for embedding: heading + stripped markdown (light cleanup)
                t = f"{doc.get('title','')} – {ch.get('heading','')}\n" + \
                    re.sub(r"```[\s\S]*?```", " ", ch["markdown"])
                t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
                t = re.sub(r"[#>*_`]", " ", t)
                t = re.sub(r"\s+", " ", t).strip()
                if t:
                    texts.append(t[:1000])
                    docs.append({
                        "url": url,
                        "markdown_url": doc.get("markdown_url", url),
                        "title": doc.get("title", ""),
                        "heading": ch.get("heading", ""),
                        "snippet": ch["markdown"][:500],
                    })
        if texts:
            self.cache.embeddings = self.embedding_model.encode(texts)
            self.cache.documents = docs
            logger.info(f"Built embeddings for {len(docs)} chunks across {len(self.cache.cache)} pages")
    
    async def warmup(self, limit: int = 120) -> None:
        """Warmup by fetching key documentation pages and building embeddings"""
        urls = await self.fetch_sitemap()
        # prioritize /reference and /docs first
        urls = [u for u in urls if u.startswith(self.base_url + "/reference")] + \
               [u for u in urls if u.startswith(self.base_url + "/docs")] + \
               [u for u in urls if "/changelog" not in u]
        seen = 0
        for u in urls:
            if seen >= limit:
                break
            doc = await self.fetch_markdown_content(u)
            if doc:
                seen += 1
        await self.build_embeddings()
    
    async def get_documentation_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Get a specific documentation page"""
        return await self.fetch_markdown_content(url)
    
    async def answer_question(self, question: str) -> Dict[str, Any]:
        """Answer a question about Voiceflow using documentation"""
        # Search for relevant documents
        relevant_docs = await self.search_documents(question, limit=3)
        
        if not relevant_docs:
            return {
                "answer": "I couldn't find relevant information in the Voiceflow documentation.",
                "sources": [],
                "confidence": 0.0
            }
        
        # Extract key information from relevant documents
        sources = []
        answer_parts = []
        
        for doc in relevant_docs:
            sources.append({
                "title": doc.get("title", ""),
                "url": doc.get("url", ""),
                "relevance": doc["similarity"]
            })
            
            # Use the chunk snippet for answers
            snippet = doc.get("snippet", "")
            heading = doc.get("heading", "")
            title = doc.get("title", "")
            
            if snippet:
                answer_parts.append(f"**{title} - {heading}**: {snippet}")
        
        answer = "\n\n".join(answer_parts) if answer_parts else f"Based on the documentation, here's what I found: {relevant_docs[0].get('snippet', 'No specific information available')}"
        
        return {
            "answer": answer,
            "sources": sources,
            "confidence": max([doc["similarity"] for doc in relevant_docs])
        }

# Initialize the MCP server
app = Server("voiceflow-docs")
voiceflow = VoiceflowMCP()

@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="search_voiceflow_docs",
            description="Search through Voiceflow documentation for specific topics, APIs, or features",
            inputSchema={
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
        ),
        Tool(
            name="get_voiceflow_doc_page",
            description="Get the content of a specific Voiceflow documentation page",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL of the documentation page (e.g., 'https://docs.voiceflow.com/docs/api-authentication')"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="ask_voiceflow_question",
            description="Ask a question about Voiceflow and get an AI-powered answer based on the documentation",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Your question about Voiceflow (e.g., 'How do I set up webhooks?', 'What are the API rate limits?')"
                    }
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="list_voiceflow_topics",
            description="Get a list of available documentation topics and categories",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[dict]:
    """Handle tool calls"""
    try:
        if name == "search_voiceflow_docs":
            query = arguments["query"]
            limit = arguments.get("limit", 5)
            
            # Ensure we have some cached content first
            if not voiceflow.cache.cache:
                logger.info("Warming up Voiceflow docs cache...")
                await voiceflow.warmup(limit=120)
            
            results = await voiceflow.search_documents(query, limit)
            
            response = f"Found {len(results)} relevant documentation chunks:\n\n"
            for i, doc in enumerate(results, 1):
                response += (
                    f"{i}. **{doc.get('title','')}** — {doc.get('heading','')}\n"
                    f"   URL: {doc.get('url')}\n"
                    f"   MD: {doc.get('markdown_url')}\n"
                    f"   Snippet: {doc.get('snippet','')[:220]}...\n"
                    f"   Relevance: {doc['similarity']:.2f}\n\n"
                )
            
            return [{"content": [{"type": "text", "text": response}]}]
        
        elif name == "get_voiceflow_doc_page":
            url = arguments["url"]
            doc = await voiceflow.get_documentation_page(url)
            
            if doc:
                response = f"# {doc['title']}\n\n"
                response += f"**URL**: {doc['url']}\n\n"
                response += f"**Markdown URL**: {doc['markdown_url']}\n\n"
                response += f"**Description**: {doc['description']}\n\n"
                response += f"**Markdown (truncated)**:\n\n{doc['raw_content'][:4000]}..."
                if len(doc['raw_content']) > 4000:
                    response += "\n\n[Content truncated - use the URL to view full content]"
            else:
                response = f"Could not fetch documentation from: {url}"
            
            return [{"content": [{"type": "text", "text": response}]}]
        
        elif name == "ask_voiceflow_question":
            question = arguments["question"]
            
            # Ensure we have some cached content first
            if not voiceflow.cache.cache:
                logger.info("Warming up Voiceflow docs cache...")
                await voiceflow.warmup(limit=120)
            
            result = await voiceflow.answer_question(question)
            
            response = f"## Answer\n\n{result['answer']}\n\n"
            
            if result['sources']:
                response += "## Sources\n\n"
                for source in result['sources']:
                    response += f"- [{source['title']}]({source['url']}) (relevance: {source['relevance']:.2f})\n"
            
            response += f"\n**Confidence**: {result['confidence']:.2f}"
            
            return [{"content": [{"type": "text", "text": response}]}]
        
        elif name == "list_voiceflow_topics":
            # Get sitemap to show available topics
            urls = await voiceflow.fetch_sitemap()
            
            # Group URLs by category
            categories = {}
            for url in urls:
                path = urlparse(url).path
                parts = [p for p in path.split('/') if p and p != 'docs']
                if parts:
                    category = parts[0] if len(parts) > 1 else 'general'
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(url)
            
            response = "## Available Voiceflow Documentation Topics\n\n"
            for category, category_urls in sorted(categories.items()):
                response += f"### {category.title()}\n"
                for url in sorted(category_urls)[:10]:  # Limit to 10 per category
                    title = url.split('/')[-1].replace('-', ' ').title()
                    response += f"- [{title}]({url})\n"
                if len(category_urls) > 10:
                    response += f"- ... and {len(category_urls) - 10} more\n"
                response += "\n"
            
            return [{"content": [{"type": "text", "text": response}]}]
        
        else:
            return [{"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}]
    
    except Exception as e:
        logger.error(f"Error in tool call {name}: {e}")
        return [{"content": [{"type": "text", "text": f"Error: {str(e)}"}]}]

async def main():
    """Main entry point"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="voiceflow-docs",
                server_version="1.0.0",
                capabilities=app.get_capabilities()
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
