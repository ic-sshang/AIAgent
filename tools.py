import json
from typing import List, Dict, Any, Optional
from base_tool import BaseTool, ToolRegistry
from database import DatabaseConnection


class StoredProcedureTool(BaseTool):
    """Tool for executing stored procedures"""
    
    def __init__(self, name: str, description: str, stored_procedure: str, 
                 parameters: List[Dict[str, Any]], db_connection: DatabaseConnection):
        """
        Initialize a stored procedure tool.
        
        Args:
            name: Tool name
            description: Tool description
            stored_procedure: Full name of the stored procedure (e.g., 'dbo.sp_GetData')
            parameters: List of parameter definitions
            db_connection: Database connection instance
        """
        super().__init__(name, description)
        self.stored_procedure = stored_procedure
        self._parameters = parameters
        self.db_connection = db_connection
    
    def get_parameters(self) -> List[Dict[str, Any]]:
        """Return parameter definitions."""
        return self._parameters
    
    def execute(self, **kwargs) -> List[Any]:
        """
        Execute the stored procedure.
        
        Args:
            **kwargs: Parameters to pass to the stored procedure
            
        Returns:
            Query results
        """
        # Build parameter list with names and values
        param_parts = []
        param_values = []
        
        for param in self._parameters:
            param_name = param['name']
            if param_name in kwargs:
                # Add parameter name with placeholder
                param_parts.append(f"@{param_name} = ?")
                param_values.append(kwargs[param_name])
        
        # Build EXEC statement with named parameters
        if param_parts:
            params_string = ', '.join(param_parts)
            query = f"EXEC {self.stored_procedure} {params_string}"
            print(f"Executing query: {query} with values: {param_values}")
            # Convert list to tuple - works for single or multiple values
            return self.db_connection.execute_query(query, tuple(param_values) if param_values else None)
        else:
            query = f"EXEC {self.stored_procedure}"
            print(f"Executing query: {query} with no parameters")
            return self.db_connection.execute_query(query)


def setup_tools(db_connection: DatabaseConnection) -> ToolRegistry:
    """
    Setup and register all tools.
    Customize this function with your actual tools.
    
    Args:
        db_connection: Database connection instance for SP tools
        
    Returns:
        ToolRegistry with all registered tools
    """
    registry = ToolRegistry()
    
    # Register Stored Procedure Tools
    registry.register(StoredProcedureTool(
        name='CustomerProfileSummary',
        description='Retrieves customer information including account number, username, email, address, invoice count, payment count and account balance',
        stored_procedure='dbo.selCustomerProfileSummary',
        parameters=[
            {
                'name': 'CustomerID',
                'type': 'integer',
                'description': 'The unique customer ID',
                'required': True
            },
            {
                'name': 'BillerUserID',
                'type': 'integer',
                'description': 'The unique biller user ID',
                'required': False
            },
            {
                'name': 'ShowInactiveInvoices',
                'type': 'boolean',
                'description': 'Whether to include inactive invoices in the results',
                'required': False
            }
        ],
        db_connection=db_connection
    ))
    
    registry.register(StoredProcedureTool(
        name='SearchCustomers',
        description='Search customers by account number, customer name, email, invoice number',
        stored_procedure='dbo.selBillerCustomerSearchBP',
        parameters=[
            {
                'name': 'BillerID',
                'type': 'integer',
                'description': 'The unique Biller ID',
                'required': True
            },
            {
                'name': 'AccountNumber',
                'type': 'string',
                'description': 'Account number to search for',
                'required': False
            },
            {
                'name': 'CustomerName',
                'type': 'string',
                'description': 'Customer name to search for',
                'required': False
            },
            {
                'name': 'EmailAddress',
                'type': 'string',
                'description': 'Customer email address to search for',
                'required': False
            },
            {
                'name': 'InvoiceNumber',
                'type': 'string',
                'description': 'Invoice number to search for',
                'required': False
            }
        ],
        db_connection=db_connection
    ))
    

    # need to update
    # registry.register(StoredProcedureTool(
    #     name='search_invoices',
    #     description='Search invoices by status, amount range, or date range',
    #     stored_procedure='dbo.sp_SearchInvoices',
    #     parameters=[
    #         {
    #             'name': 'status',
    #             'type': 'string',
    #             'description': 'Invoice status',
    #             'enum': ['paid', 'pending', 'overdue', 'cancelled'],
    #             'required': False
    #         },
    #         {
    #             'name': 'min_amount',
    #             'type': 'number',
    #             'description': 'Minimum invoice amount',
    #             'required': False
    #         },
    #         {
    #             'name': 'max_amount',
    #             'type': 'number',
    #             'description': 'Maximum invoice amount',
    #             'required': False
    #         }
    #     ],
    #     db_connection=db_connection
    # ))
    
    # registry.register(StoredProcedureTool(
    #     name='get_account_summary',
    #     description='Get summary of account including balance, payment history, and outstanding amounts',
    #     stored_procedure='dbo.sp_GetAccountSummary',
    #     parameters=[
    #         {
    #             'name': 'account_id',
    #             'type': 'integer',
    #             'description': 'The unique account ID',
    #             'required': True
    #         }
    #     ],
    #     db_connection=db_connection
    # ))
    
    # Add other types of tools here in the future
    # registry.register(CustomTool(...))
    # registry.register(APITool(...))
    # registry.register(CalculationTool(...))
    
    return registry


if __name__ == "__main__":
    # Example: Test the tool registry
    biller_id = 123
    
    with DatabaseConnection(biller_id) as db:
        registry = setup_tools(db)
        
        # Get all function definitions for Azure OpenAI
        functions = registry.get_all_function_definitions()
        print("Available Functions:")
        print(json.dumps(functions, indent=2))
        
        # List all registered tools
        print(f"\nRegistered Tools: {registry.list_tools()}")
        
        # Example: Execute a tool
        try:
            results = registry.execute(
                'get_customer_info',
                customer_id=12345
            )
            print(f"\nResults: {results}")
        except Exception as e:
            print(f"Error: {e}")
