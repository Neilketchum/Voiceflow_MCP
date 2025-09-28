# Voiceflow MCP Server - Complete Documentation

## Table of Contents
1. [What is MCP?](#what-is-mcp)
2. [Why We Built This](#why-we-built-this)
3. [How It Works](#how-it-works)
4. [Architecture Overview](#architecture-overview)
5. [Main Server Functions](#main-server-functions)
6. [Test Files Explained](#test-files-explained)
7. [Usage Examples](#usage-examples)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)

---

## What is MCP?

**MCP (Model Context Protocol)** is a standardized protocol that allows AI applications to securely connect to external data sources and tools. Think of it as a universal adapter that enables AI assistants like Cursor to access and interact with various services and documentation.

### Key MCP Benefits:
- **Standardized Interface**: One protocol for all AI tools
- **Secure Communication**: JSON-RPC over stdio with proper authentication
- **Tool Discovery**: AI can discover and use available functions dynamically
- **Real-time Interaction**: Live communication between AI and external services

### MCP in Action:
```
Cursor AI ←→ MCP Protocol ←→ Voiceflow Documentation Server
```

---

## Why We Built This

### The Problem
Voiceflow developers often need to:
- Search through extensive documentation (333+ pages)
- Get specific implementation details
- Find code examples and integration patterns
- Understand API endpoints and configurations

### The Solution
Our Voiceflow MCP Server provides:
- **Instant Access**: AI-powered search through all Voiceflow docs
- **Contextual Answers**: Intelligent responses based on documentation content
- **Chunk-Level Precision**: Find exact sections, not just entire pages
- **Markdown-First**: Clean, structured content for better AI understanding
- **Real-time Updates**: Always current with the latest documentation

### Perfect for:
- **Cursor AI**: Enhanced development assistance
- **Claude Desktop**: Voiceflow-specific knowledge
- **Any MCP-Compatible AI**: Universal Voiceflow documentation access

---

## How It Works

### 1. **Documentation Discovery**
```python
# Fetches sitemap and discovers all documentation URLs
urls = await voiceflow.fetch_sitemap()  # Finds 333+ pages
```

### 2. **Smart Content Fetching**
```python
# Tries .md URLs first, falls back to HTML
doc = await voiceflow.fetch_markdown_content(url)
```

### 3. **Intelligent Chunking**
```python
# Breaks documents into semantic chunks by headings
chunks = voiceflow.chunk_markdown(content)
```

### 4. **Semantic Search**
```python
# Uses AI embeddings for intelligent search
results = await voiceflow.search_documents(query)
```

### 5. **AI-Powered Answers**
```python
# Combines multiple chunks for comprehensive answers
answer = await voiceflow.answer_question(question)
```

---

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Cursor AI     │◄──►│  MCP Protocol    │◄──►│ Voiceflow MCP   │
│                 │    │  (JSON-RPC)      │    │    Server       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │  Documentation  │
                                               │     Cache       │
                                               └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │   Embeddings    │
                                               │   (Chunks)      │
                                               └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │ Voiceflow Docs  │
                                               │  (333+ pages)   │
                                               └─────────────────┘
```

---

## Main Server Functions

### Core Classes

#### `DocumentCache`
**Purpose**: In-memory storage for documentation content and embeddings

```python
class DocumentCache:
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}      # URL → Document data
        self.embeddings: Optional[np.ndarray] = None    # Chunk embeddings
        self.documents: List[Dict[str, Any]] = []       # Chunk metadata
```

**Key Methods**:
- `get(url)`: Retrieve cached document
- `set(url, content)`: Store document data
- `has_embeddings()`: Check if embeddings are built

#### `VoiceflowMCP`
**Purpose**: Main server class handling all Voiceflow documentation operations

```python
class VoiceflowMCP:
    def __init__(self):
        self.base_url = "https://docs.voiceflow.com"
        self.cache = DocumentCache()
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.http_client = httpx.AsyncClient()
```

### Core Functions

#### 1. `fetch_sitemap()`
**Purpose**: Discovers all available documentation pages

```python
async def fetch_sitemap(self) -> List[str]:
    """Fetch and parse the sitemap to get all documentation URLs"""
```

**How it works**:
1. Makes HTTP request to `https://docs.voiceflow.com/sitemap.xml`
2. Parses XML sitemap using ElementTree
3. Extracts all `<loc>` elements containing URLs
4. Returns list of 333+ documentation URLs

**Example Output**:
```python
[
    "https://docs.voiceflow.com/docs/authentication",
    "https://docs.voiceflow.com/docs/custom-actions",
    "https://docs.voiceflow.com/reference/authentication",
    # ... 330+ more URLs
]
```

#### 2. `fetch_markdown_content(url)`
**Purpose**: Fetches documentation content with smart fallbacks

```python
async def fetch_markdown_content(self, url: str) -> Optional[Dict[str, Any]]:
    """Fetch markdown content from a Voiceflow documentation URL"""
```

**How it works**:
1. **Check Cache**: Returns cached content if available
2. **Try .md URL**: Attempts `{url}.md` first
3. **Content Validation**: Checks if response is markdown
4. **Fallback**: Falls back to original URL if needed
5. **Rate Limiting**: Implements exponential backoff for 429/5xx errors
6. **Processing**: Extracts title, description, creates chunks
7. **Caching**: Stores processed content for future use

**Example**:
```python
# Input: "https://docs.voiceflow.com/docs/custom-actions"
# Tries: "https://docs.voiceflow.com/docs/custom-actions.md"
# Output: {
#     "url": "https://docs.voiceflow.com/docs/custom-actions",
#     "markdown_url": "https://docs.voiceflow.com/docs/custom-actions.md",
#     "title": "Custom action step",
#     "description": "The Custom Action step allows you to...",
#     "content": "cleaned markdown content",
#     "raw_content": "original markdown",
#     "chunks": [{"heading": "Overview", "markdown": "..."}, ...]
# }
```

#### 3. `chunk_markdown(md)`
**Purpose**: Intelligently splits documents into searchable chunks

```python
def chunk_markdown(self, md: str) -> List[Dict[str, Any]]:
    """Chunk markdown by headings for better search granularity"""
```

**How it works**:
1. **Line-by-line Processing**: Iterates through markdown lines
2. **Code Block Detection**: Preserves code blocks intact
3. **Heading Detection**: Uses regex to find `#`, `##`, `###` headings
4. **Chunk Creation**: Creates new chunk at each heading
5. **Content Preservation**: Maintains original formatting

**Example**:
```python
# Input markdown:
"""
# Custom Action step
Overview text here...

## Configuration
Config details...

```javascript
// Code block preserved
const action = {};
```
"""

# Output chunks:
[
    {"heading": "Custom Action step", "markdown": "# Custom Action step\nOverview text here..."},
    {"heading": "Configuration", "markdown": "## Configuration\nConfig details..."},
    {"heading": "", "markdown": "```javascript\nconst action = {};\n```"}
]
```

#### 4. `build_embeddings()`
**Purpose**: Creates AI embeddings for semantic search

```python
async def build_embeddings(self) -> None:
    """Build embeddings for all cached documents using chunks"""
```

**How it works**:
1. **Chunk Processing**: Iterates through all document chunks
2. **Text Cleaning**: Removes markdown syntax, links, code blocks
3. **Embedding Generation**: Uses SentenceTransformer to create vectors
4. **Metadata Storage**: Stores chunk metadata with embeddings
5. **Vector Storage**: Stores embeddings as NumPy array

**Text Processing Pipeline**:
```python
# Original chunk: "## Configuration\n* **name**: API key value"
# Cleaned text: "Configuration name API key value"
# Embedding: [0.1, -0.3, 0.7, ...] (384-dimensional vector)
```

#### 5. `search_documents(query, limit)`
**Purpose**: Performs semantic search through documentation

```python
async def search_documents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search through cached documents using semantic similarity"""
```

**How it works**:
1. **Query Embedding**: Converts search query to vector
2. **Similarity Calculation**: Computes cosine similarity with all chunks
3. **Ranking**: Sorts results by similarity score
4. **Filtering**: Returns top N most relevant results
5. **Metadata Enrichment**: Adds similarity scores to results

**Example**:
```python
# Query: "How to authenticate with API"
# Results:
[
    {
        "title": "Authentication",
        "heading": "API Key Setup",
        "snippet": "To authenticate with the Voiceflow API...",
        "url": "https://docs.voiceflow.com/docs/authentication",
        "markdown_url": "https://docs.voiceflow.com/docs/authentication.md",
        "similarity": 0.85
    },
    # ... more results
]
```

#### 6. `answer_question(question)`
**Purpose**: Provides AI-powered answers to questions

```python
async def answer_question(self, question: str) -> Dict[str, Any]:
    """Answer a question about Voiceflow using documentation"""
```

**How it works**:
1. **Document Search**: Finds relevant chunks using semantic search
2. **Answer Construction**: Combines multiple chunk snippets
3. **Source Attribution**: Tracks which documents were used
4. **Confidence Scoring**: Calculates overall confidence level
5. **Structured Response**: Returns formatted answer with sources

#### 7. `warmup(limit)`
**Purpose**: Pre-loads documentation for faster responses

```python
async def warmup(self, limit: int = 120) -> None:
    """Warmup by fetching key documentation pages and building embeddings"""
```

**How it works**:
1. **URL Prioritization**: Fetches `/reference` and `/docs` URLs first
2. **Batch Processing**: Downloads multiple pages in sequence
3. **Content Processing**: Extracts and chunks all content
4. **Embedding Building**: Creates searchable embeddings
5. **Cache Population**: Prepares server for fast queries

### MCP Protocol Functions

#### `handle_list_tools()`
**Purpose**: Lists available MCP tools for AI clients

```python
@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools"""
```

**Returns 4 Tools**:
1. `search_voiceflow_docs`: Search documentation
2. `get_voiceflow_doc_page`: Get specific page
3. `ask_voiceflow_question`: Ask questions
4. `list_voiceflow_topics`: Browse topics

#### `handle_call_tool(name, arguments)`
**Purpose**: Executes MCP tool calls from AI clients

```python
@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[dict]:
    """Handle tool calls"""
```

**Tool Handlers**:
- **Search**: Processes search queries with warmup and caching
- **Get Page**: Fetches specific documentation pages
- **Ask Question**: Provides AI-powered answers
- **List Topics**: Groups and displays available topics

---

## Test Files Explained

### 1. `test_server.py`
**Purpose**: Basic functionality testing

```python
# Tests core VoiceflowMCP functionality
async def test_server():
    # Test sitemap fetching
    urls = await voiceflow.fetch_sitemap()
    
    # Test document fetching
    doc = await voiceflow.fetch_markdown_content(test_url)
    
    # Test search functionality
    results = await voiceflow.search_documents(query)
    
    # Test Q&A functionality
    result = await voiceflow.answer_question(question)
```

**What it tests**:
- ✅ Sitemap parsing (333 URLs)
- ✅ Document fetching with .md URLs
- ✅ Semantic search with embeddings
- ✅ Q&A system with confidence scores
- ✅ Chunk-based search results

### 2. `test_cursor_simulation.py`
**Purpose**: Simulates Cursor's MCP communication

```python
class MCPClientSimulator:
    async def simulate_initialize_request(self):
        # Tests MCP initialization handshake
        
    async def simulate_list_tools_request(self):
        # Tests tool discovery
        
    async def simulate_search_request(self):
        # Tests search tool execution
        
    async def simulate_question_request(self):
        # Tests Q&A tool execution
```

**What it tests**:
- ✅ MCP protocol initialization
- ✅ Tool discovery and listing
- ✅ JSON-RPC request/response format
- ✅ Tool execution with real arguments
- ✅ Error handling and timeouts

### 3. `test_mcp_client.py`
**Purpose**: Simple MCP client for testing

```python
async def test_mcp_server():
    # Start MCP server process
    process = subprocess.Popen([sys.executable, "voiceflow_mcp_server.py"])
    
    # Send initialization request
    init_request = {...}
    process.stdin.write(json.dumps(init_request))
    
    # Read response
    response = process.stdout.readline()
```

**What it tests**:
- ✅ Server startup and initialization
- ✅ Basic MCP protocol communication
- ✅ Process management
- ✅ Response validation

### 4. `interactive_test.py`
**Purpose**: Interactive testing interface

```python
class InteractiveMCPTester:
    async def interactive_menu(self):
        # Provides menu-driven testing
        print("1. Search Documentation")
        print("2. Get Documentation Page")
        print("3. Ask Question")
        # ... more options
```

**What it provides**:
- ✅ Interactive menu system
- ✅ Manual tool testing
- ✅ Real-time response viewing
- ✅ User-friendly interface

### 5. `simple_test.py`
**Purpose**: Core functionality demonstration

```python
async def test_voiceflow_functionality():
    # Tests all core functions
    
async def simulate_cursor_usage():
    # Simulates real Cursor scenarios
```

**What it demonstrates**:
- ✅ Complete server functionality
- ✅ Real-world usage scenarios
- ✅ Performance metrics
- ✅ Success/failure reporting

### 6. `payload_test.py`
**Purpose**: Shows exact MCP communication

```python
class PayloadSimulator:
    def create_mcp_request(self, method: str, params: dict):
        # Creates JSON-RPC requests
        
    def create_mcp_response(self, result: dict):
        # Creates JSON-RPC responses
```

**What it shows**:
- ✅ Exact JSON-RPC request format
- ✅ Exact JSON-RPC response format
- ✅ Real payload examples
- ✅ Communication protocol details

### 7. `test_improvements.py`
**Purpose**: Tests all server improvements

```python
async def test_improvements():
    # Tests markdown-first fetching
    # Tests warmup functionality
    # Tests chunk-based search
    # Tests enhanced responses

async def test_specific_voiceflow_features():
    # Tests common Voiceflow topics
```

**What it validates**:
- ✅ Markdown-first fetching with fallbacks
- ✅ Intelligent warmup system
- ✅ Chunk-based embeddings
- ✅ Enhanced response formatting
- ✅ Production-ready features

---

## Usage Examples

### 1. Basic Search
```python
# Search for custom actions
results = await voiceflow.search_documents("custom actions", limit=3)
for result in results:
    print(f"{result['title']} - {result['heading']}")
    print(f"Snippet: {result['snippet'][:100]}...")
```

### 2. Ask Questions
```python
# Ask about authentication
answer = await voiceflow.answer_question("How do I get an API key?")
print(f"Answer: {answer['answer']}")
print(f"Confidence: {answer['confidence']:.2f}")
```

### 3. Get Specific Documentation
```python
# Get custom actions page
doc = await voiceflow.get_documentation_page(
    "https://docs.voiceflow.com/docs/custom-actions"
)
print(f"Title: {doc['title']}")
print(f"Content: {doc['raw_content'][:500]}...")
```

### 4. Warmup for Performance
```python
# Pre-load documentation
await voiceflow.warmup(limit=50)
print(f"Loaded {len(voiceflow.cache.cache)} documents")
```

---

## Configuration

### Cursor Integration
Add to your Cursor settings:

```json
{
  "mcpServers": {
    "voiceflow-docs": {
      "command": "python",
      "args": ["/path/to/voiceflow_mcp_server.py"],
      "env": {}
    }
  }
}
```

### Environment Variables
```bash
# Optional: Custom configuration
export VF_MCP_CACHE_SIZE=1000
export VF_MCP_WARMUP_LIMIT=120
export VF_MCP_TIMEOUT=30
```

---

## Troubleshooting

### Common Issues

#### 1. Server Won't Start
```bash
# Check Python version
python --version  # Should be 3.8+

# Install dependencies
pip install -r requirements.txt

# Check MCP installation
python -c "import mcp; print(mcp.__version__)"
```

#### 2. No Search Results
```python
# Ensure warmup is complete
await voiceflow.warmup(limit=50)

# Check cache status
print(f"Cache size: {len(voiceflow.cache.cache)}")
print(f"Embeddings: {voiceflow.cache.has_embeddings()}")
```

#### 3. Slow Performance
```python
# Increase warmup limit
await voiceflow.warmup(limit=200)

# Check embedding model
print(f"Model loaded: {voiceflow.embedding_model is not None}")
```

#### 4. Missing Documentation
```python
# Check sitemap access
urls = await voiceflow.fetch_sitemap()
print(f"Found {len(urls)} URLs")

# Test specific URL
doc = await voiceflow.fetch_markdown_content("https://docs.voiceflow.com/docs/custom-actions")
```

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run server with debug logging
python voiceflow_mcp_server.py
```

---

## Performance Metrics

### Typical Performance
- **Sitemap Fetch**: ~2 seconds
- **Warmup (50 docs)**: ~30 seconds
- **Search Query**: ~0.5 seconds
- **Question Answer**: ~1 second
- **Page Fetch**: ~2 seconds

### Memory Usage
- **Base Server**: ~100MB
- **With 50 docs**: ~200MB
- **With 200 docs**: ~400MB
- **With embeddings**: +100MB

### Cache Efficiency
- **Hit Rate**: ~95% after warmup
- **Miss Penalty**: ~2 seconds per miss
- **Embedding Build**: ~10 seconds for 100 docs

---

This documentation provides a complete understanding of the Voiceflow MCP Server, from high-level concepts to detailed implementation specifics. The server is designed to provide seamless, intelligent access to Voiceflow documentation for AI-powered development tools.
