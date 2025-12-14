import pyodbc
from typing import Optional
from config import get_config


class DatabaseConnection:
    """Database connection manager using biller ID for sharding"""
    
    def __init__(self, biller_id: int):
        """
        Initialize database connection for a specific biller.
        
        Args:
            biller_id: The biller ID used to determine the database shard
        """
        self.biller_id = biller_id
        self.config = get_config()
        self.connection: Optional[pyodbc.Connection] = None
        self.cursor: Optional[pyodbc.Cursor] = None
    
    def connect(self) -> pyodbc.Connection:
        """
        Establish connection to the database.
        
        Returns:
            pyodbc.Connection object
        """
        server = self.config.get('database.server')
        if not server:
            raise ValueError("Database server not configured in config.json")
        
        database = f"Shard{self.biller_id}"
        connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:{server},1433;"
            f"Database={database};"
            f"Authentication=ActiveDirectoryInteractive;"
        )
        
        try:
            self.connection = pyodbc.connect(connection_string)
            self.cursor = self.connection.cursor()
            print(f"Connected to database: {database}")
            return self.connection
        except pyodbc.Error as e:
            raise ConnectionError(f"Failed to connect to database {database}: {e}")
    
    def disconnect(self) -> None:
        """Close database connection and cursor."""
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.connection:
            self.connection.close()
            self.connection = None
            print(f"Disconnected from database: Shard{self.biller_id}")
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> list:
        """
        Execute a SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Optional tuple of parameters for parameterized queries
            
        Returns:
            List of rows
        """
        if not self.connection:
            self.connect()
        
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()
        except pyodbc.Error as e:
            raise Exception(f"Query execution failed: {e}")
    
    def execute_non_query(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query.
        
        Args:
            query: SQL query string
            params: Optional tuple of parameters for parameterized queries
            
        Returns:
            Number of rows affected
        """
        if not self.connection:
            self.connect()
        
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.connection.commit()
            return self.cursor.rowcount
        except pyodbc.Error as e:
            self.connection.rollback()
            raise Exception(f"Query execution failed: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


def get_database_connection(biller_id: int) -> DatabaseConnection:
    """
    Factory function to create a database connection for a biller.
    
    Args:
        biller_id: The biller ID
        
    Returns:
        DatabaseConnection instance
    """
    return DatabaseConnection(biller_id)


# Example usage
if __name__ == "__main__":
    # Using context manager (recommended)
    biller_id = 123
    
    try:
        with DatabaseConnection(biller_id) as db:
            # Execute a query
            results = db.execute_query("SELECT TOP 5 * FROM YourTable")
            for row in results:
                print(row)
            
            # Execute a non-query
            rows_affected = db.execute_non_query(
                "UPDATE YourTable SET column = ? WHERE id = ?",
                ('value', 1)
            )
            print(f"Rows affected: {rows_affected}")
    except Exception as e:
        print(f"Database error: {e}")
    
    # Or manual connection management
    db = DatabaseConnection(biller_id)
    try:
        db.connect()
        results = db.execute_query("SELECT COUNT(*) FROM YourTable")
        print(f"Total rows: {results[0][0]}")
    finally:
        db.disconnect()
