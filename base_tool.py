from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    def __init__(self, name: str, description: str):
        """
        Initialize a tool.
        
        Args:
            name: Tool name (used by AI for function calling)
            description: Tool description (helps AI understand when to use it)
        """
        self.name = name
        self.description = description
    
    @abstractmethod
    def get_parameters(self) -> List[Dict[str, Any]]:
        """
        Define the parameters for this tool.
        
        Returns:
            List of parameter definitions
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
        """
        pass
    
    def to_function_definition(self) -> Dict[str, Any]:
        """
        Convert tool to Azure OpenAI function calling format.
        
        Returns:
            Function definition dict
        """
        properties = {}
        required = []
        
        for param in self.get_parameters():
            prop_def = {
                'type': param['type'],
                'description': param['description']
            }
            
            # Add optional properties if they exist
            if param.get('enum'):
                prop_def['enum'] = param['enum']
            if param.get('items'):  # For array types
                prop_def['items'] = param['items']
            if param.get('properties'):  # For object types
                prop_def['properties'] = param['properties']
            
            properties[param['name']] = prop_def
            
            if param.get('required', False):
                required.append(param['name'])
        
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': {
                    'type': 'object',
                    'properties': properties,
                    'required': required if required else []
                }
            }
        }
    
    def validate_parameters(self, **kwargs) -> None:
        """
        Validate that all required parameters are provided.
        
        Args:
            **kwargs: Parameters to validate
            
        Raises:
            ValueError: If required parameters are missing
        """
        for param in self.get_parameters():
            if param.get('required', False) and param['name'] not in kwargs:
                raise ValueError(f"Missing required parameter: {param['name']}")


class ToolRegistry:
    """Registry to manage all available tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a new tool.
        
        Args:
            tool: Tool instance to register
        """
        self.tools[tool.name] = tool
        print(f"Registered tool: {tool.name}")
    
    def get(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None
        """
        return self.tools.get(name)
    
    def get_all_function_definitions(self) -> List[Dict[str, Any]]:
        """
        Get all tools as function definitions for Azure OpenAI.
        
        Returns:
            List of function definitions
        """
        return [tool.to_function_definition() for tool in self.tools.values()]
    
    def execute(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Parameters to pass to the tool
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found
        """
        tool = self.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        tool.validate_parameters(**kwargs)
        return tool.execute(**kwargs)
    
    def list_tools(self) -> List[str]:
        """
        Get list of all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self.tools.keys())
