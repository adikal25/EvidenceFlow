

## **System Overview**
This is a **Signal Prototype Agent** that automatically detects business signals (expansion, hiring, scheduling) from websites and generates personalized outreach emails. It uses a multi-agent architecture with LLM-powered agents working in sequence.

---

## **1. Entry Point: `src/app.py`**

### **`main()`**
- **Purpose**: CLI argument parser and entry point
- **Function**: Parses command line arguments (`--csv`, `--out`, `--vertical`) and calls `run_from_csv()`

### **`run_from_csv(csv_path, out, vertical)`**
- **Purpose**: Main orchestration function that processes a CSV file of domains
- **Flow**:
  1. Loads vertical-specific configuration from `configs/verticals/{vertical}.yml`
  2. Creates a LangGraph workflow using `make_graph()`
  3. Reads CSV file with domains and companies
  4. For each row, creates a `NodeState` and runs the graph
  5. Converts Pydantic objects to JSON-serializable format
  6. Writes results to output file

---

## **2. Graph Orchestration: `src/graph.py`**

### **`NodeState` Class**
- **Purpose**: State container that flows through the graph
- **Fields**: `domain`, `company`, `scrape_result`, `validate_result`, `card`, `email`

### **`make_graph(config_path, vertical_config)`**
- **Purpose**: Creates and configures the LangGraph workflow
- **Flow**:
  1. Loads configuration from YAML
  2. Creates two LLM instances (validator and outbound)
  3. Builds a 3-node graph: `scrape_node` → `validate_node` → `outbound_gate`
  4. Returns compiled graph

### **`scrape_node(state, llm)`**
- **Purpose**: First node - scrapes web pages
- **Function**: 
  - Defines candidate paths to explore (`/`, `/locations`, `/book`, etc.)
  - Calls `run_scraper_agent()` to fetch pages
  - Stores result in `state.scrape_result`

### **`validate_node(state, llm, patterns_cfg)`**
- **Purpose**: Second node - analyzes scraped content for business signals
- **Function**:
  - Checks if scraping was successful
  - Loads signal patterns from vertical config
  - Calls `run_validator_agent()` to find signals
  - If signal found, calls `build_card()` to create evidence card
  - Stores result in `state.validate_result` and `state.card`

### **`outbound_node(state, llm)`**
- **Purpose**: Third node - generates outreach email
- **Function**:
  - Checks if card exists and confidence ≥ 0.6
  - If yes, calls `draft_from_card()` to generate email
  - Stores result in `state.email`

---

## **3. Data Models: `src/schemas.py`**

### **Core Data Types**
- **`SignalType`**: Literal type for "expansion", "scheduler", "hiring"
- **`AgentResult`**: Generic result container with ok/why/confidence
- **`EvidenceCard`**: Rich evidence object with signal type, URL, snippet, confidence
- **`ScrapeResult`**: Contains scraped pages and URLs
- **`ValidateResult`**: Validation result with signal type and evidence

---

## **4. Scoring System: `src/scoring.py`**

### **`freshness_weight(published_at, weekly_decay, floor)`**
- **Purpose**: Calculates how fresh/recent the signal is
- **Function**: Applies exponential decay based on publication date
- **Formula**: `max(floor, weekly_decay^weeks)`

### **`confidence(signal_type, snippet, w)`**
- **Purpose**: Calculates confidence score for a signal
- **Function**: 
  - Base score of 0.4
  - +0.3 for explicit phrases ("grand opening", "new location")
  - +0.1 for address-like patterns
  - +0.1 for scheduler signals
  - Multiplies by freshness weight
  - Returns score and explanation

---

## **5. Scraper Agent: `src/agents/scraper_agent.py`**

### **`run_scraper_agent(domain, candidate_paths, llm, step_limit)`**
- **Purpose**: LLM-powered web scraper that fetches multiple pages
- **Flow**:
  1. Sends system prompt with tool specifications
  2. LLM generates tool calls to fetch pages
  3. Executes tool calls using `execute_tool()`
  4. Stores successful fetches in `pages` and `urls` dictionaries
  5. Returns `ScrapeResult` with collected data

### **`_try_json(line)`**
- **Purpose**: Helper to safely parse JSON from LLM responses

---

## **6. Validator Agent: `src/agents/validator_agent.py`**

### **`run_validator_agent(domain, pages, urls, patterns, llm, step_limit)`**
- **Purpose**: Analyzes scraped content to find business signals
- **Flow**:
  1. Extracts text from HTML using `extract_text()`
  2. Sends text and patterns to LLM
  3. LLM identifies strongest signal type
  4. Returns `ValidateResult` with signal details

---

## **7. Evidence Card Builder: `src/agents/evidence_card.py`**

### **`build_card(signal_type, evidence_url, snippet, published_at, screenshot_path)`**
- **Purpose**: Creates a rich evidence card from validation results
- **Function**:
  1. Calculates freshness weight
  2. Calculates confidence score
  3. Creates `EvidenceCard` with all metadata
  4. Includes explanation of scoring factors

---

## **8. Outbound Agent: `src/agents/outbound.py`**

### **`draft_from_card(llm, company, domain, signal_type, url, snippet, confidence)`**
- **Purpose**: Generates personalized outreach email
- **Flow**:
  1. Formats template with signal details
  2. Sends to LLM with email generation instructions
  3. Parses JSON response to create `EmailDraft`
  4. Falls back to generic email if parsing fails

### **`EmailDraft` Class**
- **Purpose**: Structured email container
- **Fields**: `subject`, `body`, `call_to_action`

---

## **9. Tools Protocol: `src/agents/tools_protocol.py`**

### **`execute_tool(call)`**
- **Purpose**: Executes tool calls from LLM agents
- **Tools**:
  - `fetch`: Fetches web pages
  - `extract_text`: Extracts text from HTML
  - `find_matches`: Finds text matching patterns
  - `get_meta_dates`: Extracts publication dates

---

## **10. Web Tools: `src/tools/web.py`**

### **`fetch(url, timeout, sleep_window)`**
- **Purpose**: Fetches web pages with rate limiting
- **Function**:
  1. Adds random delay to avoid rate limiting
  2. Makes HTTP request with proper headers
  3. Returns HTML content

### **`allow_fetch(url)`**
- **Purpose**: Checks if URL is allowed by robots.txt

---

## **11. Parsing Tools: `src/tools/parsing.py`**

### **`extract_text(html)`**
- **Purpose**: Extracts clean text from HTML
- **Function**: Uses readability library to get main content, then BeautifulSoup to clean

### **`sentences(text)`**
- **Purpose**: Splits text into sentences

### **`extract_date(html)`**
- **Purpose**: Extracts publication date from HTML
- **Function**: Looks for meta tags, time elements, or date patterns

---

## **12. LLM Runtime: `src/llm/ollama_runtime.py`**

### **`OllamaChat` Class**
- **Purpose**: Interface to local Ollama LLM server
- **Function**: Sends chat messages to Ollama API and returns responses

### **`OllamaConfig` Class**
- **Purpose**: Configuration for LLM parameters (model, temperature, tokens)

---

## **Complete Data Flow**

CSV → NodeState → LangGraph → Agent1 → LLM → JSON Response → Agent2 → LLM → JSON Response → Final JSON Output


**Key Features:**
- **Multi-agent architecture** with specialized agents
- **LLM-powered decision making** at each step
- **Confidence scoring** with freshness weighting
- **Designed for error handling** and fallbacks
- **JSON-serializable output** for integration
- **Configurable patterns** per vertical/industry

