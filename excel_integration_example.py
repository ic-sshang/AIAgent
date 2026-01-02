"""
Example of adding Excel export tools to your agent
Add this to your tools.py setup_tools() function
"""

from excel_tool import ExcelExportTool, ExcelExportFromQueryTool

def setup_tools_with_excel(db_connection):
    """Example of registering Excel export tools"""
    from tools import setup_tools
    
    # Get existing tools
    registry = setup_tools(db_connection)
    
    # Add Excel export tools
    registry.register(ExcelExportTool(output_dir="exports"))
    registry.register(ExcelExportFromQueryTool(db_connection, output_dir="exports"))
    
    return registry


# Update your prompt to mention Excel export capability
EXCEL_PROMPT_ADDITION = (
    "\n\nYou can export data to Excel files when users request it. "
    "Use the ExportToExcel tool to export data, or QueryToExcel to run a query and export directly. "
    "Always inform the user of the file path where the Excel file was saved."
)
