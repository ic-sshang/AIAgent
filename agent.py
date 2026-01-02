import os
import json
from typing import List, Dict, Any
from openai import AzureOpenAI
from config import get_config
from database import DatabaseConnection
from prompt import SYSTEM_PROMPT
from tools import setup_tools
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
class AIAgent:
    """Azure OpenAI Agent with function calling capabilities"""
    
    def __init__(self, biller_id: int):
        """
        Initialize the AI Agent.
        
        Args:
            biller_id: The biller ID for database connection
        """
        self.biller_id = biller_id
        self.config = get_config()
        self.db_connection = DatabaseConnection(biller_id)
        self.db_connection.connect()
        self.tool_registry = setup_tools(self.db_connection)
        
        # Initialize Azure OpenAI client
        api_key = os.getenv('AI_KEY')
        if not api_key:
            raise ValueError("AI_KEY not found in environment variables")
        
        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=self.config.get('ai.api_version', '2025-01-01'),
            azure_endpoint=self.config.get('ai.base_url')
        )
        
        self.model = self.config.get('ai.model_name', 'gpt-4o-mini')
        self.conversation_history: List[Dict[str, Any]] = []
        self.last_query_results: List[Dict[str, Any]] = []  # Cache for most recent query results
    
    def __del__(self):
        """Cleanup database connection."""
        if hasattr(self, 'db_connection') and self.db_connection:
            self.db_connection.disconnect()
    
    def chat(self, user_message: str) -> str:
        """
        Send a message to the AI agent and get a response.
        
        Args:
            user_message: The user's message/prompt
            
        Returns:
            The agent's response
        """
        # Add user message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Get available functions
        functions = self.tool_registry.get_all_function_definitions()
        
        # Allow multiple rounds of tool calls for multi-step reasoning
        # Scale max iterations based on number of tools (allow more complex chains)
        max_iterations = min(10, max(5, len(functions) // 4))  # Dynamic limit: 5-10 based on tool count
        iteration = 0
        consecutive_no_progress = 0
        
        print(f"Starting chat with max {max_iterations} iterations for {len(functions)} available tools")
        
        while iteration < max_iterations:
            iteration += 1
            
            # Make API call
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.conversation_history,
                    tools=functions,
                    tool_choice="auto"
                )
            except Exception as e:
                print(f"Error during OpenAI API call: {str(e)}")
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            # If no tool calls, we have the final answer
            if not tool_calls:
                assistant_message = response_message.content
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })
                print(f"Completed in {iteration} iterations")
                return assistant_message
            
            # Reset no-progress counter when we have tool calls
            consecutive_no_progress = 0
            
            # Add assistant's message with tool calls to history
            self.conversation_history.append(response_message)
            
            # Execute each tool call
            any_success = False
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Log arg details for debugging
                if function_name == 'ExportToExcel' and 'data' in function_args:
                    data_count = len(function_args['data']) if isinstance(function_args['data'], list) else 0
                    print(f"[Iteration {iteration}/{max_iterations}] Calling tool: {function_name} with {data_count} data records")
                else:
                    print(f"[Iteration {iteration}/{max_iterations}] Calling tool: {function_name} with args: {function_args}")
                
                try:
                    # Execute the tool
                    results = self.tool_registry.execute(
                        function_name,
                        **function_args
                    )
                    
                    # Cache query results for potential Excel export
                    # Convert to dict format for proper Excel export
                    if isinstance(results, list) and len(results) > 0 and function_name != 'ExportToExcel':
                        # Convert database rows to dictionaries
                        cached_data = []
                        for row in results:
                            if hasattr(row, '__iter__') and not isinstance(row, (str, dict)):
                                # It's a database row - convert to dict using cursor description
                                if hasattr(self.db_connection.cursor, 'description') and self.db_connection.cursor.description:
                                    columns = [column[0] for column in self.db_connection.cursor.description]
                                    cached_data.append(dict(zip(columns, row)))
                                else:
                                    # Fallback to list if no column names
                                    cached_data.append(list(row))
                            elif isinstance(row, dict):
                                # Already a dict
                                cached_data.append(row)
                            else:
                                cached_data.append(row)
                        
                        self.last_query_results = cached_data
                        print(f"[Cache] Stored {len(cached_data)} records from {function_name} as dictionaries")
                    
                    # For Excel export, if data is missing or incomplete, use cached results
                    if function_name == 'ExportToExcel':
                        data_arg = function_args.get('data', [])
                        if not data_arg and self.last_query_results:
                            print(f"[Excel] No data provided, using {len(self.last_query_results)} cached records")
                            function_args['data'] = self.last_query_results
                            results = self.tool_registry.execute(function_name, **function_args)
                        elif isinstance(data_arg, list) and self.last_query_results:
                            if len(data_arg) < len(self.last_query_results):
                                print(f"[Excel] WARNING: Only {len(data_arg)} records provided, but cache has {len(self.last_query_results)} records")
                                print(f"[Excel] Using complete cached data instead")
                                function_args['data'] = self.last_query_results
                                results = self.tool_registry.execute(function_name, **function_args)
                    
                    # Log result details
                    if isinstance(results, list):
                        print(f"[Iteration {iteration}/{max_iterations}] Tool returned {len(results)} records")
                    elif isinstance(results, dict):
                        if 'rows_exported' in results:
                            print(f"[Iteration {iteration}/{max_iterations}] Excel export: {results.get('rows_exported', 0)} rows")
                    
                    # Format results
                    function_response = self._format_results(results)
                    print(f"[Iteration {iteration}/{max_iterations}] Tool response: {function_response[:200]}...")
                    any_success = True
                    
                except Exception as e:
                    function_response = f"Error executing {function_name}: {str(e)}"
                    print(f"[Iteration {iteration}/{max_iterations}] Error: {function_response}")
                
                # Add function response to conversation
                self.conversation_history.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response
                })
            
            # Track progress - if no tools succeeded, increment counter
            if not any_success:
                consecutive_no_progress += 1
                if consecutive_no_progress >= 3:
                    print(f"Stopping: No progress made in {consecutive_no_progress} consecutive iterations")
                    return "I encountered errors while processing your request. Please try rephrasing your question."
            
            # Continue loop to check if more tool calls are needed
        
        # If we hit max iterations, return a message
        print(f"Reached max iterations ({max_iterations})")
        return "I've completed multiple steps but reached the iteration limit. Please ask a follow-up question if you need more information."
    
    def _format_results(self, results: Any) -> str:
        """Format tool results as JSON string."""
        if not results:
            return "No results found."
        
        # If results is already a dict (e.g., from Excel export tool), return it as-is
        if isinstance(results, dict):
            return json.dumps(results, default=str, indent=2)
        
        # If it's not a list, convert to string
        if not isinstance(results, list):
            return str(results)
        
        # Convert results to list of dicts if possible
        formatted_results = []
        for row in results:
            if hasattr(row, 'cursor_description'):
                # Has column names
                columns = [column[0] for column in row.cursor_description]
                formatted_results.append(dict(zip(columns, row)))
            else:
                # Just raw values
                formatted_results.append(list(row))
        
        return json.dumps(formatted_results, default=str, indent=2)
    
    def reset_conversation(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
    
    def add_system_message(self, message: str) -> None:
        """Add a system message to set context."""
        self.conversation_history.insert(0, {
            "role": "system",
            "content": message
        })


def main():
    """Example usage of the AI Agent"""
    # Set biller ID
    biller_id = 1537
    
    # Create agent
    agent = AIAgent(biller_id)
    
    # Add system message to set context
    # agent.add_system_message(
    #     "You are a helpful assistant that helps users query database information. "
    #     "Use the available tools to retrieve data from stored procedures when needed. If some parameters you need are not provided, ask the user for them, DO NOT make assumptions."
    #     f"Always provide clear and concise responses. BillerID is {agent.biller_id}. Use this BillerID for any database calls that require BillerID. Only use {agent.biller_id} for SP requires parameter BillerID Not the BillerUserID."
    #     f"current date is {datetime.now().strftime('%Y-%m-%d')}."
    # )
    agent.add_system_message(SYSTEM_PROMPT.format(
        biller_id=agent.biller_id,
        current_date=datetime.now().strftime('%Y-%m-%d')
    ))
    print("AI Agent started. Type 'quit' to exit.\n")
    
    # Interactive loop
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not user_input:
            continue
        
        try:
            response = agent.chat(user_input)
            print(f"\nAssistant: {response}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
