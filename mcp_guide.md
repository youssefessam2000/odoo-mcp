# MCP — The Beginner's Guide
### From Zero to Understanding Model Context Protocol

---

## 1. What Problem Does MCP Solve?

Imagine you're talking to Claude (the AI) and you say:

> "Show me my timesheets from last week"

Without MCP, Claude would say:
> "I'm sorry, I don't have access to your Odoo system."

With MCP, Claude says:
> "Sure! Here are your 5 timesheet entries from last week..."

**MCP is the bridge between AI and your real data/systems.**

Before MCP existed, every developer had to invent their own way to connect AI to external tools. MCP is a standard that everyone agrees on — like USB is a standard for connecting devices.

---

## 2. The Simple Mental Model

Think of MCP like a **TV remote control**:

```
You (viewer)
    │  press button
    ▼
Remote Control (Claude)
    │  sends signal
    ▼
TV (MCP Server)
    │  executes command
    ▼
Result shown on screen
```

- **You** = the user chatting
- **Claude** = understands your words, decides what to do
- **MCP Server** = the actual worker that does things
- **Result** = Claude reads it and responds to you

---

## 3. Core Concepts

### 3.1 MCP Server
A program YOU build that exposes capabilities to AI assistants.

In our project, `main.py` is the MCP server. It runs in the background and waits for Claude to call its tools.

```
main.py  ←  this is your MCP server
```

### 3.2 Tools
Functions inside your MCP server that Claude can call.

Think of tools like buttons on a remote. Each button does one specific thing:

| Tool Name | What It Does |
|---|---|
| `authenticate` | Log in to Odoo |
| `list_my_timesheets` | Get timesheet entries |
| `create_timesheet` | Create a new entry |
| `update_timesheet` | Edit an entry |
| `delete_timesheet` | Remove an entry |

Claude sees these tools and decides when to use them based on what you say.

### 3.3 MCP Client
The AI assistant that connects to your MCP server. In our case: **Claude Desktop**.

### 3.4 Transport (How They Talk)
MCP servers and clients need to communicate. The most common way is **STDIO**:

```
Claude  ──── stdin/stdout pipe ────  MCP Server
```

STDIO means they talk through the terminal's input/output. It's fast and simple.

---

## 4. How a Tool Call Works (Step by Step)

Let's trace what happens when you say **"create a timesheet for 3 hours on project 233"**:

```
Step 1:  You type the message in Claude chat

Step 2:  Claude reads it and thinks:
         "The user wants to create a timesheet.
          I have a tool called create_timesheet.
          I'll call it with hours=3, project_id=233"

Step 3:  Claude sends this to MCP server:
         {
           "tool": "create_timesheet",
           "arguments": {
             "name": "Work session",
             "hours": 3,
             "project_id": 233,
             "task_id": 103304,
             "date": "2026-04-02"
           }
         }

Step 4:  MCP server receives it, runs create_timesheet()
         which calls Odoo's XML-RPC create() function

Step 5:  Odoo creates the record and returns:
         { "created_id": 98765 }

Step 6:  MCP server sends result back to Claude

Step 7:  Claude reads the result and responds to you:
         "Done! Created a 3-hour timesheet entry.
          The record ID is 98765."
```

---

## 5. What's Inside Our MCP Server

Our project has two files that matter:

### main.py — The MCP Server
This file defines all the tools. Here's a simplified version of one tool:

```python
@mcp.tool()
def create_timesheet(name, date, hours, project_id, task_id):
    """Create a new timesheet entry."""
    record_id = client.create_timesheet(...)
    return { "created_id": record_id }
```

The `@mcp.tool()` decorator is what registers the function as a tool that Claude can see and call. Without it, Claude wouldn't know the function exists.

### odoo_client.py — The Worker
This file does the actual work — talking to Odoo via XML-RPC. main.py asks it to do things, it executes them and returns results.

```
main.py (MCP layer)
    │  calls
    ▼
odoo_client.py (Odoo layer)
    │  calls
    ▼
Odoo XML-RPC
```

---

## 6. The MCP Inspector (What You Saw)

The Inspector UI you opened with `mcp dev main.py` is a **testing dashboard**. It lets you:

- See all your tools listed
- Call a tool manually with custom inputs
- See the raw request and response
- Debug problems without needing Claude

Think of it like Postman — but for MCP tools instead of REST APIs.

### What the Inspector Panels Mean

| Panel | What It Shows |
|---|---|
| Tools (left) | All tools your server exposes |
| Input (middle) | Parameters you can fill in |
| Result (right) | What the tool returned |
| History (bottom) | All calls made this session |
| Server Notifications | Logs and errors from your server |

---

## 7. MCP vs Other Approaches

### MCP vs REST API
```
REST API:
  You build endpoints → someone calls them manually
  GET /timesheets, POST /timesheets/create

MCP:
  You build tools → AI calls them automatically based on conversation
  Claude figures out WHEN and HOW to call them
```

### MCP vs Plugin/Extension
```
Browser Extension:
  Works only in one app (the browser)

MCP:
  Works with any AI client that supports it
  (Claude Desktop, Cursor, Zed, etc.)
```

### MCP vs Function Calling (OpenAI style)
```
OpenAI Function Calling:
  Tied to OpenAI's API, non-standard

MCP:
  Open standard, works with multiple AI providers
  Any AI that speaks MCP can use your server
```

---

## 8. The .env File — Why It Matters

Your `.env` file stores sensitive information:

```
ODOO_BASE_URL=https://erp.envnt.co
ODOO_DB=codlab
ODOO_EMAIL=Youssef.Essam@codelabsys.com
ODOO_API_KEY=your_secret_key
```

**Rules:**
- Never share this file
- Never commit it to Git (add `.env` to `.gitignore`)
- The `.env.example` file is the safe version you can share — it has the keys but no real values

---

## 9. Authentication Flow in Our Server

```
1. .env file is loaded on startup
       │
       ▼
2. OdooClient is created with credentials
       │
       ▼
3. First tool call triggers authenticate()
       │
       ▼
4. XML-RPC call to /xmlrpc/2/common
   authenticate(db, email, api_key)
       │
       ▼
5. Odoo returns uid (user ID number)
   e.g. uid = 1784
       │
       ▼
6. All future calls use uid + api_key
   No need to re-authenticate
```

**Why API key instead of password?**

- A password gives full account access
- An API key can be revoked without changing your password
- If your API key leaks, you just delete it and generate a new one
- More secure for automated systems

---

## 10. How to Add a New Tool

Want to add a tool that lists all projects? It's 3 steps:

**Step 1: Add method to odoo_client.py**
```python
def list_projects(self) -> list:
    return self._execute(
        model="project.project",
        method="search_read",
        args=[[]],
        kwargs={"fields": ["id", "name"], "limit": 100},
    )
```

**Step 2: Add tool to main.py**
```python
@mcp.tool()
def list_projects() -> list:
    """List all available projects in Odoo."""
    return client.list_projects()
```

**Step 3: Restart the inspector and test**

That's it. Claude will now know about this tool and use it when you ask about projects.

---

## 11. Connecting to Claude Desktop

Once you're done testing in the Inspector, connect to Claude Desktop so you can use your tools in normal chat:

**1. Find the config file:**
```
Windows: C:\Users\YOUR_NAME\AppData\Roaming\Claude\claude_desktop_config.json
```

**2. Add your server:**
```json
{
  "mcpServers": {
    "odoo-timesheet": {
      "command": "py",
      "args": ["D:/projects/odoo-mcp/main.py"]
    }
  }
}
```

**3. Restart Claude Desktop**

**4. You'll see a tools icon in Claude chat** — click it to see your tools are connected.

Now you can just chat normally:
- *"Show me my timesheets from March"*
- *"Create a 2 hour timesheet for task 103304 today"*
- *"Delete timesheet entry 98765"*

---

## 12. Key Vocabulary Summary

| Term | Simple Definition |
|---|---|
| MCP | A standard protocol for connecting AI to external tools |
| MCP Server | Your program that exposes tools to AI |
| MCP Client | The AI assistant (Claude Desktop, Cursor, etc.) |
| Tool | A function Claude can call |
| STDIO | How Claude and your server communicate (via terminal pipes) |
| Transport | The communication method between client and server |
| Inspector | A browser UI for testing your MCP tools |
| XML-RPC | How our server talks to Odoo (remote function calls) |
| API Key | A secure token for authentication instead of a password |
| uid | Odoo's user ID number returned after authentication |
| `.env` | File storing your secret credentials locally |

---

## 13. What to Learn Next

Now that you understand the basics, here's a learning path:

1. **Add more Odoo tools** — projects, tasks, employees
2. **Learn about MCP Resources** — expose data as readable documents, not just function calls
3. **Learn about MCP Prompts** — pre-built conversation templates
4. **Deploy your MCP server** — run it on a server so your whole team can use it
5. **Read the official docs** — modelcontextprotocol.io

---

*Built with Python · Connects to Odoo 14 via XML-RPC · Served via MCP STDIO transport*
