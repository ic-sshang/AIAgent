"""
Excel Export Tool for AI Agent
Generates Excel files from database query results
"""

from typing import List, Dict, Any
from base_tool import BaseTool
import pandas as pd
from datetime import datetime
import os


class ExcelExportTool(BaseTool):
    """Tool for exporting query results to Excel"""
    
    def __init__(self, output_dir: str = "exports", api_base_url: str = "http://localhost:8000"):
        super().__init__(
            name='ExportToExcel',
            description='Export data you already have to an Excel file. Use this to save results from a previous tool call (like SearchCustomers or SearchPayments) to Excel. Pass the array of data objects in the data parameter. DO NOT use this to execute new queries - only to export existing data.'
        )
        self.output_dir = output_dir
        self.api_base_url = api_base_url
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def get_parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'data',
                'type': 'array',
                'description': 'Array of data objects/records to export. Each object should have consistent keys/columns.',
                'items': {
                    'type': 'object'
                },
                'required': True
            },
            {
                'name': 'filename',
                'type': 'string',
                'description': 'Name for the Excel file (without extension)',
                'required': False
            },
            {
                'name': 'sheet_name',
                'type': 'string',
                'description': 'Name for the worksheet/sheet in the Excel file',
                'required': False
            }
        ]
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Export data to Excel file.
        
        Args:
            data: List of dictionaries containing the data
            filename: Optional filename (without extension)
            sheet_name: Optional sheet name
            
        Returns:
            Dictionary with file path and export details
        """
        data = kwargs.get('data', [])
        filename = kwargs.get('filename', f'export_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        sheet_name = kwargs.get('sheet_name', 'Sheet1')
        
        if not data:
            return {
                'success': False,
                'message': 'No data provided to export'
            }
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Generate file path
            file_path = os.path.join(self.output_dir, f"{filename}.xlsx")
            
            # Export to Excel
            df.to_excel(file_path, sheet_name=sheet_name, index=False, engine='openpyxl')
            
            # Get absolute path and download URL
            abs_path = os.path.abspath(file_path)
            download_url = f"{self.api_base_url}/download/{filename}.xlsx"
            
            return {
                'success': True,
                'message': f'Data exported successfully to Excel. Download your file using the link below.',
                'download_url': download_url,
                'filename': f"{filename}.xlsx",
                'rows_exported': len(df),
                'columns': list(df.columns)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error exporting to Excel: {str(e)}'
            }


class ExcelExportFromQueryTool(BaseTool):
    """Tool that executes a query and exports results directly to Excel"""
    
    def __init__(self, db_connection, output_dir: str = "exports", api_base_url: str = "http://localhost:8000"):
        super().__init__(
            name='QueryToExcel',
            description='Execute a NEW database query and export the results directly to an Excel file in one step. Only use this when you need to query fresh data specifically for export. If you already have data from a previous tool call, use ExportToExcel instead.'
        )
        self.db_connection = db_connection
        self.output_dir = output_dir
        self.api_base_url = api_base_url
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def get_parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'query',
                'type': 'string',
                'description': 'SQL query to execute (SELECT statement or EXEC stored procedure)',
                'required': True
            },
            {
                'name': 'filename',
                'type': 'string',
                'description': 'Name for the Excel file (without extension)',
                'required': False
            }
        ]
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute query and export to Excel.
        
        Args:
            query: SQL query to execute
            filename: Optional filename
            
        Returns:
            Dictionary with file path and export details
        """
        query = kwargs.get('query')
        filename = kwargs.get('filename', f'query_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        
        try:
            # Execute query
            results = self.db_connection.execute_query(query)
            
            if not results:
                return {
                    'success': False,
                    'message': 'Query returned no results'
                }
            
            # Convert to DataFrame
            # Get column names from cursor description
            columns = [column[0] for column in self.db_connection.cursor.description]
            df = pd.DataFrame.from_records(results, columns=columns)
            
            # Generate file path
            file_path = os.path.join(self.output_dir, f"{filename}.xlsx")
            
            # Export to Excel
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            # Get absolute path and download URL
            abs_path = os.path.abspath(file_path)
            download_url = f"{self.api_base_url}/download/{filename}.xlsx"
            
            return {
                'success': True,
                'message': f'Query results exported successfully to Excel. Download your file using the link below.',
                'download_url': download_url,
                'filename': f"{filename}.xlsx",
                'rows_exported': len(df),
                'columns': list(df.columns)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error exporting query to Excel: {str(e)}'
            }


# Example usage in tools.py setup
if __name__ == "__main__":
    from database import DatabaseConnection
    
    # Test export
    biller_id = 1537
    
    with DatabaseConnection(biller_id) as db:
        # Example 1: Export query results
        export_tool = ExcelExportFromQueryTool(db, output_dir="exports")
        
        result = export_tool.execute(
            query="EXEC dbo.selCustomerProfileSummary @CustomerID = 7984",
            filename="customer_profile"
        )
        
        print(f"Export result: {result}")
        
        # Example 2: Export data from Python
        sample_data = [
            {'Name': 'John', 'Email': 'john@example.com', 'Count': 5},
            {'Name': 'Jane', 'Email': 'jane@example.com', 'Count': 3}
        ]
        
        excel_tool = ExcelExportTool(output_dir="exports")
        result2 = excel_tool.execute(
            data=sample_data,
            filename="sample_data",
            sheet_name="Customers"
        )
        
        print(f"Export result: {result2}")
