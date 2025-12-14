# Azure AI Agent with Function Calling

This project implements an extensible Azure OpenAI agent that can call various tools based on user prompts. Tools can be stored procedures, API calls, calculations, or any custom functionality.

## Architecture

The system uses a modular tool architecture:
- **BaseTool**: Abstract base class for all tools
- **ToolRegistry**: Manages and executes tools
- **StoredProcedureTool**: Specific implementation for database stored procedures
- **Custom Tools**: Easy to add any type of tool

## Setup

1. Install dependencies:
```powershell
pip install -r requirements.txt
```

2. Configure your environment:
   - Update `.env` with your Azure OpenAI API key
   - Update `config.json` with your database server and AI endpoint

3. Define your tools in `tools.py`

## Adding Tools

### Stored Procedure Tool
```python
from tools import StoredProcedureTool

registry.register(StoredProcedureTool(
    name='get_customer_info',
    description='Retrieves customer information',
    stored_procedure='dbo.sp_GetCustomerInfo',
    parameters=[
        {
            'name': 'customer_id',
            'type': 'integer',
            'description': 'The unique customer ID',
            'required': True
        }
    ],
    db_connection=db_connection
))
```

### Custom Tool (API, Calculation, etc.)
```python
from base_tool import BaseTool

class MyCustomTool(BaseTool):
    def __init__(self):
        super().__init__(
            name='my_tool',
            description='What this tool does'
        )
    
    def get_parameters(self):
        return [
            {
                'name': 'param1',
                'type': 'string',
                'description': 'Parameter description',
                'required': True
            }
        ]
    
    def execute(self, **kwargs):
        # Your tool logic here
        return {"result": "data"}

# Register it
registry.register(MyCustomTool())
```

See `custom_tools_example.py` for more examples (API tools, calculators, date/time tools, business logic).

## Usage

Run the interactive agent:
```powershell
python agent.py
```

Example prompts:
- "Get customer information for customer ID 12345"
- "Show me billing history for customer 67890"
- "Calculate 15% of 200"
- "What's the weather in Seattle?"

## Files

- `agent.py` - Main AI agent with function calling
- `base_tool.py` - Base tool class and registry (core framework)
- `tools.py` - Tool definitions and setup
- `custom_tools_example.py` - Examples of custom tools
- `database.py` - Database connection manager
- `config.py` - Configuration loader
- `config.json` - Configuration file
- `.env` - Environment variables (API keys)

## Extending the System

1. Create a new tool by inheriting from `BaseTool`
2. Implement `get_parameters()` and `execute()` methods
3. Register it in `setup_tools()` function
4. The AI agent automatically discovers and uses it!
