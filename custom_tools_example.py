"""
Example: How to add custom tools to the agent
"""

from typing import List, Dict, Any
from base_tool import BaseTool, ToolRegistry
import requests
from datetime import datetime


# Example 1: API Tool
class WeatherTool(BaseTool):
    """Tool for getting weather information via API"""
    
    def __init__(self):
        super().__init__(
            name='get_weather',
            description='Get current weather information for a city'
        )
    
    def get_parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'city',
                'type': 'string',
                'description': 'The city name',
                'required': True
            },
            {
                'name': 'units',
                'type': 'string',
                'description': 'Temperature units (metric or imperial)',
                'enum': ['metric', 'imperial'],
                'required': False
            }
        ]
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        city = kwargs.get('city')
        units = kwargs.get('units', 'metric')
        
        # Example API call (you would use a real API)
        # response = requests.get(f'https://api.weather.com/...')
        # return response.json()
        
        return {
            'city': city,
            'temperature': 22,
            'units': units,
            'condition': 'Sunny'
        }


# Example 2: Calculation Tool
class CalculatorTool(BaseTool):
    """Tool for performing mathematical calculations"""
    
    def __init__(self):
        super().__init__(
            name='calculate',
            description='Perform mathematical calculations including basic arithmetic and percentages'
        )
    
    def get_parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'operation',
                'type': 'string',
                'description': 'The operation to perform',
                'enum': ['add', 'subtract', 'multiply', 'divide', 'percentage'],
                'required': True
            },
            {
                'name': 'operand1',
                'type': 'number',
                'description': 'The first number',
                'required': True
            },
            {
                'name': 'operand2',
                'type': 'number',
                'description': 'The second number',
                'required': True
            }
        ]
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        operation = kwargs.get('operation')
        operand1 = kwargs.get('operand1')
        operand2 = kwargs.get('operand2')
        
        operations = {
            'add': lambda a, b: a + b,
            'subtract': lambda a, b: a - b,
            'multiply': lambda a, b: a * b,
            'divide': lambda a, b: a / b if b != 0 else None,
            'percentage': lambda a, b: (a / b) * 100 if b != 0 else None
        }
        
        result = operations[operation](operand1, operand2)
        
        return {
            'operation': operation,
            'operand1': operand1,
            'operand2': operand2,
            'result': result
        }


# Example 3: Date/Time Tool
class DateTimeTool(BaseTool):
    """Tool for date and time operations"""
    
    def __init__(self):
        super().__init__(
            name='get_datetime_info',
            description='Get current date/time or calculate date differences'
        )
    
    def get_parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'action',
                'type': 'string',
                'description': 'The action to perform',
                'enum': ['current', 'format', 'days_between'],
                'required': True
            },
            {
                'name': 'date1',
                'type': 'string',
                'description': 'First date in YYYY-MM-DD format',
                'required': False
            },
            {
                'name': 'date2',
                'type': 'string',
                'description': 'Second date in YYYY-MM-DD format',
                'required': False
            }
        ]
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        action = kwargs.get('action')
        
        if action == 'current':
            return {
                'current_datetime': datetime.now().isoformat(),
                'current_date': datetime.now().date().isoformat(),
                'current_time': datetime.now().time().isoformat()
            }
        elif action == 'days_between':
            date1_str = kwargs.get('date1')
            date2_str = kwargs.get('date2')
            
            date1 = datetime.fromisoformat(date1_str)
            date2 = datetime.fromisoformat(date2_str)
            
            days = (date2 - date1).days
            
            return {
                'date1': date1_str,
                'date2': date2_str,
                'days_between': days
            }
        
        return {}


# Example 4: Custom Business Logic Tool
class DiscountCalculatorTool(BaseTool):
    """Tool for calculating discounts based on business rules"""
    
    def __init__(self):
        super().__init__(
            name='calculate_discount',
            description='Calculate discount amount based on customer type and purchase amount'
        )
    
    def get_parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'customer_type',
                'type': 'string',
                'description': 'Type of customer',
                'enum': ['regular', 'premium', 'vip'],
                'required': True
            },
            {
                'name': 'purchase_amount',
                'type': 'number',
                'description': 'Total purchase amount',
                'required': True
            }
        ]
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        customer_type = kwargs.get('customer_type')
        purchase_amount = kwargs.get('purchase_amount')
        
        # Business logic for discounts
        discount_rates = {
            'regular': 0.05,  # 5%
            'premium': 0.10,  # 10%
            'vip': 0.15       # 15%
        }
        
        # Additional discount for large purchases
        if purchase_amount > 1000:
            discount_rates[customer_type] += 0.05
        
        discount_rate = discount_rates.get(customer_type, 0)
        discount_amount = purchase_amount * discount_rate
        final_amount = purchase_amount - discount_amount
        
        return {
            'customer_type': customer_type,
            'original_amount': purchase_amount,
            'discount_rate': discount_rate,
            'discount_amount': discount_amount,
            'final_amount': final_amount
        }


# How to register these tools in your setup_tools function:
def register_custom_tools(registry: ToolRegistry):
    """
    Register custom tools to the registry.
    Call this from your setup_tools() function in tools.py
    """
    registry.register(WeatherTool())
    registry.register(CalculatorTool())
    registry.register(DateTimeTool())
    registry.register(DiscountCalculatorTool())
