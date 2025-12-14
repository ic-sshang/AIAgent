import os
import json
from typing import List, Dict, Any
from openai import AzureOpenAI
from config import get_config
from database import DatabaseConnection
from tools import setup_tools


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
        
        # Initial API call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.conversation_history,
            tools=functions,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        # Process function calls
        if tool_calls:
            # Add assistant's message with tool calls to history
            self.conversation_history.append(response_message)
            
            # Execute each tool call
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"Calling tool: {function_name} with args: {function_args}")
                
                try:
                    # Execute the tool
                    results = self.tool_registry.execute(
                        function_name,
                        **function_args
                    )
                    
                    # Format results
                    function_response = self._format_results(results)
                    
                except Exception as e:
                    function_response = f"Error executing {function_name}: {str(e)}"
                
                # Add function response to conversation
                self.conversation_history.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response
                })
            
            # Get final response from the model
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history
            )
            
            final_message = final_response.choices[0].message.content
            self.conversation_history.append({
                "role": "assistant",
                "content": final_message
            })
            
            return final_message
        else:
            # No function call needed
            assistant_message = response_message.content
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            return assistant_message
    
    def _format_results(self, results: List[Any]) -> str:
        """Format database results as JSON string."""
        if not results:
            return "No results found."
        
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
    biller_id = 123
    
    # Create agent
    agent = AIAgent(biller_id)
    
    # Add system message to set context
    agent.add_system_message(
        "You are a helpful assistant that helps users query database information. "
        "Use the available tools to retrieve data from stored procedures when needed. "
        "Always provide clear and concise responses."
    )
    
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
