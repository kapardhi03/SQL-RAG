# SQL-RAG: Enhanced SQL Query Generation with RA
> Transform natural language questions into intelligent database queries using Retrieval-Augmented Generation (RAG) and Large Language Models.

---

##  **Project Overview**
SQL-RAG is an intelligent system that enables users to query SQL databases using natural language, powered by Retrieval-Augmented Generation (RAG) and large language models. The system seamlessly converts user questions into executable SQL statements, executes them on databases, and synthesizes clear, context-rich answers from the results.

### **Key Innovation**
By integrating RAG, SQL-RAG enhances the accuracy and relevance of responses by grounding language model outputs in real, up-to-date data, making database interactions conversational and intuitive.

---

##  **Features**

- **🗣️ Natural Language Querying**: Ask questions in plain English, get structured data answers
- ** Intelligent Table Selection**: Automatically identifies relevant tables for your query
- ** Semantic Search Support**: Vector similarity search for conceptual queries
- **⚡ Real-time Query Execution**: Fast and efficient SQL generation and execution
- ** Error Recovery**: Automatic query correction with detailed error handling
- ** Multi-Model Support**: Compatible with GPT-4, Gemini, Claude, and other LLMs
- ** High Accuracy**: 100% faithfulness and 83.1% answer correctness
- ** Enterprise Ready**: Built for production with PostgreSQL and vector support

---

##  **Use Cases**

### **Business Intelligence & Analytics**
- Generate instant insights from complex databases without SQL expertise
- Create real-time reports and dashboards through conversational queries

### **Customer Support Automation**
- Power intelligent chatbots that retrieve information from support databases
- Provide instant answers to customer queries with accurate data retrieval

### **Employee Self-Service Portals**
- Enable employees to access HR, payroll, and policy information conversationally
- Reduce dependency on technical support staff

### **Healthcare Data Retrieval**
- Assist clinicians in extracting patient statistics and treatment histories
- Support epidemiological research with natural language database queries

### **Sales & Marketing Reporting**
- Generate real-time performance reports and KPI tracking
- Analyze campaign effectiveness through conversational database access

---

##  **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Frontend     │    │     Backend     │    │   PostgreSQL    │
│                 │    │                 │    │    Database     │
│ • Chat Interface│◄──►│ • LangGraph     │◄──►│ • Vector Store  │
│ • Query Input   │    │   Agent         │    │ • Table Schema  │
│ • Results UI    │    │ • RAG Pipeline  │    │ • Sample Data   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   LLM Models    │
                    │                 │
                    │ • GPT-4         │
                    │ • Gemini        │
                    │ • Claude        │
                    └─────────────────┘
```

### **Workflow Process**

1.  Table Selection**: Identify relevant tables using metadata analysis
2.  Query Generation**: Create SQL queries (semantic or standard)
3.  Core Subject Extraction**: Extract key concepts for vector search (if needed)
4.  Query Execution**: Execute SQL with automatic error handling
5.  Response Generation**: Convert results to natural language

---
##  **Installation**

### **Prerequisites**
- Python 3.8+
- PostgreSQL 13+ with vector extension
- Node.js 16+ (for frontend)

### **Backend Setup**

```bash
# Clone the repository
git clone https://github.com/your-repo/sql-rag.git
cd sql-rag

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database and API keys
```

### **Database Setup**

```sql
-- Create PostgreSQL database with vector extension
CREATE DATABASE sql_rag_db;
\c sql_rag_db;
CREATE EXTENSION vector;

-- Run migration scripts
python manage.py migrate
```

### **Frontend Setup**

```bash
cd frontend
npm install
npm run dev
```

---

##  **Configuration**

### **Environment Variables**

```env
# Database Configuration
POSTGRES_DSN=postgresql://user:password@localhost:5432/sql_rag_db

# LLM API Keys
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_gemini_api_key
ANTHROPIC_API_KEY=your_claude_api_key

# Application Settings
DEBUG=False
HOST=localhost
PORT=8000
```

### **Model Configuration**

```python
# Supported models
AVAILABLE_MODELS = {
    "gpt-4": "OpenAI GPT-4",
    "gemini-2.0": "Google Gemini 2.0",
    "claude-3.5": "Anthropic Claude 3.5"
}
```

---

# Core Innovations

## 1. Hybrid Search with Reciprocal Rank Fusion (RRF)

```python
class HybridSearchEngine:
    def search(self, query):
        # Parallel search execution
        semantic_results = self.vector_search(query)
        keyword_results = self.keyword_search(query)

        # RRF scoring
        for rank, result in enumerate(semantic_results):
            result.score += 1.0 / (rank + 1)
        for rank, result in enumerate(keyword_results):
            result.score += 1.0 / (rank + 1)

        return self.merge_and_rank(semantic_results, keyword_results)
````

**Key Insight**: RRF handles cases where one search method completely misses relevant results while the other finds them, improving overall recall by **40%**.

---

## 2. Dynamic Strategy Selection with LangGraph

```python
class SQLGenerationAgent:
    def select_strategy(self, query_complexity, schema_info):
        if query_complexity.score < 0.3:
            return "template_based"
        elif query_complexity.score < 0.7:
            return "semantic_translation"
        else:
            return "multi_step_decomposition"

    def generate_sql(self, strategy, query):
        agent = self.strategy_agents[strategy]
        return agent.process(query)
```

---

## 3. Error Recovery Pipeline

```python
class ErrorRecoverySystem:
    def handle_sql_error(self, error, original_query, generated_sql):
        error_type = self.classify_error(error)
        if error_type == "syntax":
            return self.syntax_correction_agent(error, generated_sql)
        elif error_type == "schema":
            return self.schema_correction_agent(error, original_query)
        elif error_type == "semantic":
            return self.semantic_correction_agent(error, original_query)
        return self.escalate_to_human(error, original_query)
```

```

---
##  **Usage**

### **Basic Query Examples**

```python
# Example 1: Simple data retrieval
query = "What are the dairy products under 5% GST?"
response = await agent.ainvoke({"user_query": query})
# Output: "The dairy products under 5% GST are: Milk (₹45.00), Butter (₹120.00)..."

# Example 2: Aggregate analysis
query = "What's the average price of electronics?"
response = await agent.ainvoke({"user_query": query})
# Output: "The average price of electronics is ₹15,750..."

# Example 3: Complex joins
query = "Show me customers who bought products worth more than ₹10,000 last month"
response = await agent.ainvoke({"user_query": query})
```

### **API Usage**

```bash
# REST API endpoint
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the top selling products this quarter?"}'
```

### **Web Interface**

1. Navigate to `http://localhost:3000`
2. Select your preferred LLM model
3. Type your question in natural language
4. View results with SQL query breakdown

---

##  **Performance Metrics**

Our evaluation demonstrates high-quality results across key metrics:

| Metric | Score | Description |
|--------|-------|-------------|
| **Faithfulness** | 100% | Responses are completely grounded in retrieved data |
| **Answer Correctness** | 83.1% | High accuracy in answering user questions |
| **Context Recall** | 81.7% | Excellent retrieval of relevant information |
| **Context Precision** | 66.7% | Good precision in information relevance |

---

##  **Technical Details**

### **Core Components**

- **LangGraph Agent**: Orchestrates the workflow with state management
- **Vector Embeddings**: Semantic search using PostgreSQL's vector extension
- **Query Parser**: Intelligent SQL generation with error correction
- **RAG Pipeline**: Combines retrieval and generation for accurate responses

### **Supported SQL Features**

-  SELECT queries with complex JOINs
-  Aggregation functions (SUM, AVG, COUNT, etc.)
-  Vector similarity search with `<=>` operator
-  Filtering and sorting operations
-  Subqueries and CTEs
-  Dynamic schema adaptation

### **Error Handling**

```python
# Automatic retry mechanism
if query_execution_fails:
    error_context = capture_error_details()
    corrected_query = regenerate_sql_with_error_context(error_context)
    retry_execution(corrected_query)
```
## WorkFlow
![image](https://github.com/user-attachments/assets/d896b16e-c219-4278-8bce-32835c712af0)


---

##  **API Reference**

### **Main Endpoint**

```http
POST /api/query
Content-Type: application/json

{
  "query": "string",
  "model": "string (optional)",
  "config": {
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

### **Response Format**

```json
{
  "success": true,
  "data": {
    "answer": "Natural language response",
    "sql_query": "Generated SQL statement",
    "results": [...],
    "metadata": {
      "execution_time": "1.2s",
      "tables_used": ["products", "categories"],
      "query_type": "semantic"
    }
  }
}
```

---

##  **Future Scope**

### **Planned Enhancements**

- ** Multi-Database Support**: Federated querying across different database types
- ** Enhanced Security**: Advanced data privacy and access control features
- ** Performance Optimization**: Query caching and result optimization
- ** Mobile App**: Native mobile applications for on-the-go querying
- ** Advanced AI**: Integration with latest LLM models and techniques

### **Current Challenges**

- **Query Complexity**: Handling highly complex or ambiguous natural language queries
- **Schema Evolution**: Dynamic adaptation to changing database schemas
- **Scale Performance**: Optimizing performance for large-scale databases
- **Data Quality**: Managing incomplete or noisy data during retrieval

---

### **Development Setup**

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Code formatting
black src/
isort src/

# Type checking
mypy src/
```

### **Project Structure**

```
sql-rag/
├── src/
│   ├── agents/          # LangGraph agents and workflows
│   ├── models/          # Database models and schemas
│   ├── api/             # REST API endpoints
│   └── utils/           # Utility functions
├── frontend/            # React.js frontend application
├── tests/               # Test suites
├── docs/                # Documentation
└── requirements.txt     # Python dependencies
```

![image](https://github.com/user-attachments/assets/f673e4ee-6f60-49bd-9ad8-4845cf3bfead)

![image](https://github.com/user-attachments/assets/f4d32349-e02b-45f1-8103-379a4fdc26e3)

---

**⭐ Star this repository if you find it helpful!**
