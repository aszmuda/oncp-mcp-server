# **Requirements: Application Resolution MCP Server**

## **1\. Project Overview**

The goal is to build a Model Context Protocol (MCP) server using Python and the fastmcp library. This server acts as a gateway between an LLM and an external FastAPI Service. The MCP server allows the LLM to trigger asynchronous resolution jobs for application issues, check their status, and retrieve the reasoning (agentic thought process) behind the fixes.

The project will be managed using uv for high-performance dependency management and packaging. The server will expose a Server-Sent Events (SSE) endpoint to allow clients to connect over HTTP.

## **2\. Technology Stack**

* **Language:** Python 3.12+  
* **Package & Project Manager:** uv (for dependency management, virtual environments, and running the server)  
* **Core Library:** fastmcp (High-level framework for building MCP servers)  
* **HTTP Client:** httpx (for making async calls to the FastAPI service)  
* **Environment Management:** python-dotenv (for configuration)

## **3\. External Service Integration (The FastAPI Service)**

The MCP server must interact with a downstream FastAPI service.

Base URL Configuration:  
The URL for this service must be configurable via environment variable: RESOLUTION\_API\_URL.  
**API Endpoints Contract:**

### **3.1. Launch Resolution Job**

* **Method:** POST  
* **Path:** /resolve (assumed path, configurable)  
* **Request Body (JSON):**  
  {  
    "error": "error code or short error message",  
    "hostname": "target hostname or service identifier",  
    "message": "message describing the issue to fix"  
  }

* **Expected Response:**  
  {  
    "job\_id": "unique-job-uuid",  
    "status": "QUEUED"  
  }

### **3.2. Get Job Status**

* **Method:** GET  
* **Path:** /jobs/{job\_id}/status  
* **Expected Response:**  
  {  
    "job\_id": "unique-job-uuid",  
    "status": "RUNNING" // e.g., QUEUED, RUNNING, COMPLETED, FAILED  
  }

### **3.3. Get Agent Analysis**

* **Method:** GET  
* **Path:** /jobs/{job\_id}/analysis  
* **Expected Response:**  
  {  
    "job\_id": "unique-job-uuid",  
    "thoughts": "Markdown or text string describing the agent's diagnosis and actions."  
  }

## **4\. MCP Tool Definitions**

The server must expose the following three tools to the MCP client (LLM).

### **Tool 1: start\_resolution**

* **Description:** Triggers an asynchronous analysis and resolution agent for a specific application issue.  
* **Arguments:**  
  * hostname (String, Required): The hostname, IP, or identifier of the system experiencing issues.  
  * error\_code (String, Required): The specific error code or short error identifier.  
  * issue\_description (String, Required): Contextual message describing the issue.  
* **Behavior:**  
  1. Constructs the payload: {"error": error\_code, "hostname": hostname, "message": issue\_description}.  
  2. Sends a POST request to the external API.  
  3. Returns the job\_id to the user so they can track progress.

### **Tool 2: check\_resolution\_status**

* **Description:** Checks the current status of a running resolution job.  
* **Arguments:**  
  * job\_id (String, Required): The ID returned by start\_resolution.  
* **Behavior:**  
  1. Calls the external status endpoint.  
  2. Returns the current state (e.g., "Processing", "Completed").

### **Tool 3: get\_resolution\_reasoning**

* **Description:** Retrieves the AI agent's detailed thought process, root cause analysis, and steps taken during the resolution.  
* **Arguments:**  
  * job\_id (String, Required): The ID returned by start\_resolution.  
* **Behavior:**  
  1. Calls the external analysis endpoint.  
  2. Returns the text content of the agent's logs/thoughts.

## **5\. Implementation Details**

* **FastMCP Usage:** Use the @mcp.tool() decorator to define the tools.  
* **Transport Protocol:** The server must be configured to expose an **SSE (Server-Sent Events) endpoint**. While standard input/output (stdio) is default for local agents, this implementation specifically requires SSE support for remote/HTTP-based clients.  
* **Async/Await:** All tool implementations must be async to prevent blocking the MCP server while waiting for HTTP responses.  
* **Error Handling:**  
  * If the external API is unreachable, return a clear user-facing error string.  
  * If the external API returns a 4xx or 5xx error, capture the response body and return it as part of the tool output.  
* **Input Validation:** Ensure arguments are non-empty strings.

## **6\. Configuration (Env Vars)**

The application must support a .env file containing:

* RESOLUTION\_SERVICE\_URL: Base URL of the FastAPI service (e.g., http://localhost:8000).  
* API\_TIMEOUT: (Optional) Timeout in seconds for HTTP requests (default: 30).  
* MCP\_SSE\_PORT: (Optional) Port to run the SSE server on (default: 8000 or similar).

## **7\. Deliverables**

1. pyproject.toml: The project configuration file managed by uv.  
2. uv.lock: The lock file ensuring reproducible builds.  
3. main.py: The entry point for the FastMCP server (configured for SSE).  
4. client.py: An internal helper module for handling HTTP interaction with the FastAPI service.  
5. .env.example: Template for environment variables.