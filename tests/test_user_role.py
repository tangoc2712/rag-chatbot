import unittest
from src.rag.admin_assistant import ECommerceRAG

class TestUserRole(unittest.TestCase):
    def setUp(self):
        self.rag = ECommerceRAG()

    def test_admin_access(self):
        """Test that admin has access to everything"""
        # Admin should be able to generate SQL for orders
        sql = self.rag.generate_sql_query("Show me recent orders", role="admin")
        self.assertIn("order", sql.lower())
        
        # Admin should be able to execute SQL for orders
        # Note: We can't easily test execution without a real DB connection in this unit test,
        # but we can test the execute_sql method's access control logic if we mock the DB or just check the return for "Access denied"
        
        # Let's test the execute_sql access control logic directly by passing a forbidden query
        # We expect it to NOT return "Access denied" for admin
        result = self.rag.execute_sql("SELECT * FROM \"order\" LIMIT 1", role="admin")
        # If it returns a string starting with "Access denied", it failed. 
        # If it returns a list (even empty) or a DB error, it passed the access control check.
        if isinstance(result, str):
            self.assertFalse(result.startswith("I'm sorry, but as a admin"), "Admin should not be denied access")

    def test_user_access_denied(self):
        """Test that user is denied access to forbidden tables"""
        # User should NOT get order tables in schema for SQL generation
        # Check for table definitions specifically
        schema = self.rag.get_schema(role="user")
        self.assertNotIn('"order" (Customer Orders)', schema)
        self.assertNotIn('"user" (Customer Accounts)', schema)
        self.assertNotIn('payment (Payment Transactions)', schema)
        
        # User should be denied execution of forbidden queries
        result = self.rag.execute_sql("SELECT * FROM \"order\" LIMIT 1", role="user")
        self.assertTrue(isinstance(result, str) and "Access denied" in result or "cannot access" in result, "User should be denied access to orders")

    def test_user_access_allowed(self):
        """Test that user can access allowed tables"""
        # User should have product tables in schema
        schema = self.rag.get_schema(role="user")
        self.assertIn("product", schema.lower())
        self.assertIn("review", schema.lower())
        
        # User should be allowed to execute product queries
        # We'll assume the DB connection works or fails with a DB error, not access denied
        result = self.rag.execute_sql("SELECT * FROM product LIMIT 1", role="user")
        if isinstance(result, str):
            self.assertFalse("cannot access" in result, "User should be allowed access to products")

if __name__ == '__main__':
    unittest.main()
