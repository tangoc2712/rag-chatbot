import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.rag.admin_assistant import ECommerceRAG
from src.api.endpoints.products import search_products
from src.api.endpoints.orders import get_customer_orders

class TestDBImplementation(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cursor
        
    @patch('src.rag.assistant.psycopg2.connect')
    @patch('src.rag.assistant.genai')
    def test_rag_semantic_search(self, mock_genai, mock_connect):
        # Setup mocks
        mock_connect.return_value = self.mock_conn
        mock_genai.embed_content.return_value = {'embedding': [0.1, 0.2, 0.3]}
        self.mock_cursor.fetchall.return_value = [{'product_title': 'Test Product', 'distance': 0.1}]
        
        # Initialize RAG
        rag = ECommerceRAG()
        rag.settings.GOOGLE_API_KEY = "fake_key"
        
        # Test search
        results = rag.semantic_search("test query")
        
        # Verify
        mock_genai.embed_content.assert_called_once()
        self.mock_cursor.execute.assert_called_once()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['product_title'], 'Test Product')

    @patch('src.api.endpoints.orders.get_db_connection')
    async def test_api_get_orders(self, mock_get_db):
        # Setup mocks
        mock_get_db.return_value = self.mock_conn
        self.mock_cursor.fetchall.return_value = [{'order_id': '123'}]
        
        # Test endpoint
        results = await get_customer_orders(123)
        
        # Verify
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['order_id'], '123')

if __name__ == '__main__':
    unittest.main()
