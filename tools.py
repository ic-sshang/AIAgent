import json
from typing import List, Dict, Any, Optional
from base_tool import BaseTool, ToolRegistry
from database import DatabaseConnection
from excel_tool import ExcelExportFromQueryTool, ExcelExportTool


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

class QueryTool(BaseTool):
    """Tool for executing arbitrary SQL queries"""

    def __init__(self, name: str, description: str, query: str, parameters: List[Dict[str, Any]], db_connection: DatabaseConnection):
        """
        Initialize a query tool.
        
        Args:
            name: Tool name
            description: Tool description
            query: SQL query string
            parameters: List of parameter definitions
            db_connection: Database connection instance
        """
        super().__init__(name, description)
        self.query = query
        self._parameters = parameters
        self.db_connection = db_connection

    def execute(self, params: Optional[tuple] = None) -> List[Any]:
        """
        Execute an arbitrary SQL query.
        
        Args:
            query: SQL query string
            params: Optional[tuple] = None
            
        Returns:
            Query results
        """
        print(f"Executing query: {self.query} with params: {params}")
        return self.db_connection.execute_query(self.query, params)
    
    def get_parameters(self) -> List[Dict[str, Any]]:
        return self._parameters

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
        description='Retrieves customer information including account number, username, email, address, invoice count, payment count and account balance, CustomerID has to get from SearchCustomers tool first.',
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
        name='SearchInvoices',
        description='Search invoices by invoice number, account number, customer name, invoice type Id, etc.',
        stored_procedure='dbo.selCustomerInvoiceSearchBP',
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
                'name': 'InvoiceNumber',
                'type': 'string',
                'description': 'Invoice number to search for',
                'required': False
            },
            {
                'name': 'InvoiceTypeID',
                'type': 'integer',
                'description': 'Invoice type ID to search for',
                'required': False
            },
            {
                'name': 'Outstanding',
                'type': 'boolean',
                'description': 'Whether to filter for outstanding invoices only',
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
    
    registry.register(StoredProcedureTool(
        name='SearchPayments',
        description='Search payments by account number, customer name, invoice number, approval indicator',
        stored_procedure='dbo.selCustomerPaymentSearch',
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
                'name': 'ApprovalInd',
                'type': 'boolean',
                'description': 'Approval indicator to search for',
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
    
    registry.register(StoredProcedureTool(
        name='GetInvoiceCountAndVolume',
        description='Get total invoice count and amount by date range, invoice type ID.',
        stored_procedure='AcctRpt.GetInvoiceCountsAndVolume',
        parameters=[
            {
                'name': 'BillerID',
                'type': 'integer',
                'description': 'The unique Biller ID',
                'required': True
            },
            {
                'name': 'InvoiceTypeID',
                'type': 'integer',
                'description': 'Invoice type ID to filter by',
                'required': True
            },
            {
                'name': 'StartDate',
                'type': 'string',
                'description': 'Start date to filter by in YYYY-MM-DD format',
                'required': True
            },
            {
                'name': 'EndDate',
                'type': 'string',
                'description': 'End date to filter by in YYYY-MM-DD format',
                'required': True
            }
        ],
        db_connection=db_connection
    ))
   
    registry.register(StoredProcedureTool(
        name='GetPaymentACHVolume',
        description='Get total ACH payment amount by date range and invoice type ID.',
        stored_procedure='AcctRpt.GetPaymentACHVolume',
        parameters=[
            {
                'name': 'BillerID',
                'type': 'integer',
                'description': 'The unique Biller ID',
                'required': True
            },
            {
                'name': 'InvoiceTypeID',
                'type': 'integer',
                'description': 'Invoice type ID to filter by',
                'required': True
            },
            {
                'name': 'StartDate',
                'type': 'string',
                'description': 'Start date to filter by in YYYY-MM-DD format',
                'required': True
            },
            {
                'name': 'EndDate',
                'type': 'string',
                'description': 'End date to filter by in YYYY-MM-DD format',
                'required': True
            }
        ],
        db_connection=db_connection
    ))
   
    registry.register(StoredProcedureTool(
        name='GetPaymentACHCount',
        description='Get total ACH payment count by date range and invoice type ID.',
        stored_procedure='AcctRpt.GetPaymentACHCount',
        parameters=[
            {
                'name': 'BillerID',
                'type': 'integer',
                'description': 'The unique Biller ID',
                'required': True
            },
            {
                'name': 'InvoiceTypeID',
                'type': 'integer',
                'description': 'Invoice type ID to filter by',
                'required': True
            },
            {
                'name': 'StartDate',
                'type': 'string',
                'description': 'Start date to filter by in YYYY-MM-DD format',
                'required': True
            },
            {
                'name': 'EndDate',
                'type': 'string',
                'description': 'End date to filter by in YYYY-MM-DD format',
                'required': True
            }
        ],
        db_connection=db_connection
    ))

    registry.register(StoredProcedureTool(
        name='GetPaymentCreditCardVolume',
        description='Get total credit card payment amount by date range and invoice type ID.',
        stored_procedure='AcctRpt.GetPaymentCCVolume',
        parameters=[
            {
                'name': 'BillerID',
                'type': 'integer',
                'description': 'The unique Biller ID',
                'required': True
            },
            {
                'name': 'InvoiceTypeID',
                'type': 'integer',
                'description': 'Invoice type ID to filter by',
                'required': True
            },
            {
                'name': 'StartDate',
                'type': 'string',
                'description': 'Start date to filter by in YYYY-MM-DD format',
                'required': True
            },
            {
                'name': 'EndDate',
                'type': 'string',
                'description': 'End date to filter by in YYYY-MM-DD format',
                'required': True
            }
        ],
        db_connection=db_connection
    ))

    registry.register(StoredProcedureTool(
        name='GetPaymentCreditCardCount',
        description='Get total credit card payment count by date range and invoice type ID.',
        stored_procedure='AcctRpt.GetPaymentCCCount',
        parameters=[
            {
                'name': 'BillerID',
                'type': 'integer',
                'description': 'The unique Biller ID',
                'required': True
            },
            {
                'name': 'InvoiceTypeID',
                'type': 'integer',
                'description': 'Invoice type ID to filter by',
                'required': True
            },
            {
                'name': 'StartDate',
                'type': 'string',
                'description': 'Start date to filter by in YYYY-MM-DD format',
                'required': True
            },
            {
                'name': 'EndDate',
                'type': 'string',
                'description': 'End date to filter by in YYYY-MM-DD format',
                'required': True
            }
        ],
        db_connection=db_connection
    ))

    registry.register(StoredProcedureTool(
        name='GetPaymentOnlineBankDirectCountAndVolume',
        description='Get total online bank direct payment amount and count by date range and invoice type ID.',
        stored_procedure='AcctRpt.GetPaymentObdCOUNTANDVolume',
        parameters=[
            {
                'name': 'BillerID',
                'type': 'integer',
                'description': 'The unique Biller ID',
                'required': True
            },
            {
                'name': 'InvoiceTypeID',
                'type': 'integer',
                'description': 'Invoice type ID to filter by',
                'required': True
            },
            {
                'name': 'StartDate',
                'type': 'string',
                'description': 'Start date to filter by in YYYY-MM-DD format',
                'required': True
            },
            {
                'name': 'EndDate',
                'type': 'string',
                'description': 'End date to filter by in YYYY-MM-DD format',
                'required': True
            }
        ],
        db_connection=db_connection
    ))

    registry.register(StoredProcedureTool(
        name='GetPaymentCOUNTANDVolumeByPaymentSource',
        description='Get total payment amount and count by date range, invoice type ID and payment source ID. Must get payment source and invoice type from user, not IDs. Invoice Type ID cannot be 0 or -1, Payment Source ID cannot be 0.',
        stored_procedure='AcctRpt.GetPaymentCOUNTANDVolumeByPaymentSource',
        parameters=[
            {
                'name': 'BillerID',
                'type': 'integer',
                'description': 'The unique Biller ID',
                'required': True
            },
            {
                'name': 'InvoiceTypeID',
                'type': 'integer',
                'description': 'Invoice type ID to filter by',
                'required': True
            },
            {
                'name': 'StartDate',
                'type': 'string',
                'description': 'Start date to filter by in YYYY-MM-DD format',
                'required': True
            },
            {
                'name': 'EndDate',
                'type': 'string',
                'description': 'End date to filter by in YYYY-MM-DD format',
                'required': True
            },
             {
                'name': 'PaymentSourceID',
                'type': 'integer',
                'description': 'The unique Payment Source ID',
                'required': True
            },
        ],
        db_connection=db_connection
    ))

    registry.register(QueryTool(
        name='GetInvoiceTypes',
        description='Execute a custom SQL query to get invoice type ID based on invoice type description',
        query='select * from tblInvoiceType',
        parameters=[],
        db_connection=db_connection
    ))

    registry.register(QueryTool(
        name='GetPaymentSources',
        description='Execute a custom SQL query to get payment source ID based on payment source description',
        query='select * from tblPaymentSource',
        parameters=[],
        db_connection=db_connection
    ))

    registry.register(ExcelExportTool(output_dir="exports", api_base_url="http://localhost:8000"))
    registry.register(ExcelExportFromQueryTool(db_connection, output_dir="exports", api_base_url="http://localhost:8000"))

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
