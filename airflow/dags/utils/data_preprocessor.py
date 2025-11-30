"""
Data preprocessing utilities for Airflow DAGs.
Handles preprocessing of product and order data for embedding generation.
"""
import logging
import pandas as pd
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Preprocesses product and order data for embedding generation.
    Adapts logic from migrate_db.py to work with PostgreSQL records.
    """
    
    @staticmethod
    def preprocess_product_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Preprocess product records from PostgreSQL.
        
        Args:
            records: List of product dictionaries from database
            
        Returns:
            DataFrame with preprocessed products and combined_text for embedding
        """
        if not records:
            logger.warning("No product records to preprocess")
            return pd.DataFrame()
        
        logger.info(f"Preprocessing {len(records)} product records")
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Create combined text field for semantic search
        # Use existing fields if available, otherwise create from components
        if 'combined_text' not in df.columns or df['combined_text'].isna().all():
            df['combined_text'] = (
                df['product_title'].fillna('').astype(str).str.strip() + ' ' +
                df['description'].fillna('').astype(str).str.strip() + ' ' +
                df['category'].fillna('').astype(str).str.strip()
            )
            logger.info("Generated combined_text from product fields")
        
        # Ensure combined_text is not empty
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        
        logger.info(f"Preprocessed {len(df)} products with valid combined_text")
        return df
    
    @staticmethod
    def preprocess_order_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Preprocess order records from PostgreSQL.
        
        Args:
            records: List of order dictionaries from database
            
        Returns:
            DataFrame with preprocessed orders and text for embedding
        """
        if not records:
            logger.warning("No order records to preprocess")
            return pd.DataFrame()
        
        logger.info(f"Preprocessing {len(records)} order records")
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Create text field for embedding
        # Concatenate: Product + Product_Category + Order_Priority
        df['embedding_text'] = (
            df['product'].fillna('').astype(str).str.strip() + ' ' +
            df['product_category'].fillna('').astype(str).str.strip() + ' ' +
            df['order_priority'].fillna('').astype(str).str.strip()
        )
        
        # Ensure embedding_text is not empty
        df['embedding_text'] = df['embedding_text'].str.strip()
        df = df[df['embedding_text'] != '']
        
        logger.info(f"Preprocessed {len(df)} orders with valid embedding_text")
        return df
    
    # ==================== Cloud PostgreSQL Preprocessing Functions ====================
    
    @staticmethod
    def preprocess_cloud_product_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess cloud products: name + description + category_id + price"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            df['name'].fillna('').astype(str) + ' ' +
            df['description'].fillna('').astype(str) + ' ' +
            'Category: ' + df['category_id'].fillna('').astype(str) + ' ' +
            'Price: ' + df['price'].fillna(0).astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} cloud products")
        return df
    
    @staticmethod
    def preprocess_cloud_category_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess categories: name + type + parent_category_id"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            df['name'].fillna('').astype(str) + ' ' +
            'Type: ' + df['type'].fillna('').astype(str) + ' ' +
            'Parent: ' + df['parent_category_id'].fillna('').astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} categories")
        return df
    
    @staticmethod
    def preprocess_cloud_review_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess reviews: product + rating + review_text + reviewer"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            'Product: ' + df['product_id'].fillna('').astype(str) + ' ' +
            'Rating: ' + df['rating'].fillna(0).astype(str) + '/5 ' +
            df['review_text'].fillna('').astype(str) + ' ' +
            'User: ' + df['user_id'].fillna('').astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} reviews")
        return df
    
    @staticmethod
    def preprocess_cloud_user_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess users: full_name + email + job + gender"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            df['full_name'].fillna('').astype(str) + ' ' +
            df['email'].fillna('').astype(str) + ' ' +
            'Job: ' + df['job'].fillna('').astype(str) + ' ' +
            'Gender: ' + df['gender'].fillna('').astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} users")
        return df
    
    @staticmethod
    def preprocess_cloud_order_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess orders: order_id + status + order_total + items + customer"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            'Order: ' + df['order_id'].fillna('').astype(str) + ' ' +
            'Status: ' + df['status'].fillna('').astype(str) + ' ' +
            'Total: ' + df['order_total'].fillna(0).astype(str) + ' ' +
            'Customer: ' + df['user_id'].fillna('').astype(str) + ' ' +
            'Date: ' + df['created_at'].fillna('').astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} orders")
        return df
    
    @staticmethod
    def preprocess_cloud_order_item_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess order items: order + product + quantity + unit_price"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            'Order: ' + df['order_id'].fillna('').astype(str) + ' ' +
            'Product: ' + df['product_id'].fillna('').astype(str) + ' ' +
            'Qty: ' + df['quantity'].fillna(0).astype(str) + ' ' +
            'Price: ' + df['unit_price'].fillna(0).astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} order items")
        return df
    
    @staticmethod
    def preprocess_cloud_cart_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess carts: user + status + total_price + items"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            'User: ' + df['user_id'].fillna('').astype(str) + ' ' +
            'Status: ' + df['status'].fillna('').astype(str) + ' ' +
            'Total: ' + df['total_price'].fillna(0).astype(str) + ' ' +
            'Date: ' + df['created_at'].fillna('').astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} carts")
        return df
    
    @staticmethod
    def preprocess_cloud_cart_item_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess cart items: cart + product + quantity + unit_price"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            'Cart: ' + df['cart_id'].fillna('').astype(str) + ' ' +
            'Product: ' + df['product_id'].fillna('').astype(str) + ' ' +
            'Qty: ' + df['quantity'].fillna(0).astype(str) + ' ' +
            'Price: ' + df['unit_price'].fillna(0).astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} cart items")
        return df
    
    @staticmethod
    def preprocess_cloud_payment_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess payments: payment_id + amount + method + status"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            'Payment: ' + df['payment_id'].fillna('').astype(str) + ' ' +
            'Amount: ' + df['amount'].fillna(0).astype(str) + ' ' +
            'Method: ' + df['method'].fillna('').astype(str) + ' ' +
            'Status: ' + df['status'].fillna('').astype(str) + ' ' +
            'Order: ' + df['order_id'].fillna('').astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} payments")
        return df
    
    @staticmethod
    def preprocess_cloud_shipment_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess shipments: tracking + carrier_id + status + delivery_date"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            'Tracking: ' + df['tracking_number'].fillna('').astype(str) + ' ' +
            'Carrier: ' + df['carrier_id'].fillna('').astype(str) + ' ' +
            'Status: ' + df['status'].fillna('').astype(str) + ' ' +
            'Shipped: ' + df['shipped_at'].fillna('').astype(str) + ' ' +
            'Delivered: ' + df['delivered_at'].fillna('').astype(str) + ' ' +
            'Order: ' + df['order_id'].fillna('').astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} shipments")
        return df
    
    @staticmethod
    def preprocess_cloud_inventory_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess inventory: product + warehouse_id + quantity"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            'Product: ' + df['product_id'].fillna('').astype(str) + ' ' +
            'Warehouse: ' + df['warehouse_id'].fillna('').astype(str) + ' ' +
            'Stock: ' + df['quantity'].fillna(0).astype(str) + ' ' +
            'Updated: ' + df['last_updated'].fillna('').astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} inventory records")
        return df
    
    @staticmethod
    def preprocess_cloud_coupon_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess coupons: code + discount_type + value + validity"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            'Code: ' + df['code'].fillna('').astype(str) + ' ' +
            'Type: ' + df['discount_type'].fillna('').astype(str) + ' ' +
            'Value: ' + df['value'].fillna(0).astype(str) + ' ' +
            'Valid: ' + df['valid_from'].fillna('').astype(str) + ' to ' + df['valid_to'].fillna('').astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} coupons")
        return df
    
    @staticmethod
    def preprocess_cloud_event_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess events: event_type + user + session + metadata"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            'Event: ' + df['event_type'].fillna('').astype(str) + ' ' +
            'User: ' + df['user_id'].fillna('').astype(str) + ' ' +
            'Session: ' + df['session_id'].fillna('').astype(str) + ' ' +
            'Time: ' + df['ts'].fillna('').astype(str) + ' ' +
            'Metadata: ' + df['metadata'].fillna('').astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} events")
        return df
    
    @staticmethod
    def preprocess_cloud_role_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Preprocess roles: role_name + is_active + permissions"""
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['combined_text'] = (
            'Role: ' + df['role_name'].fillna('').astype(str) + ' ' +
            'Active: ' + df['is_active'].fillna(False).astype(str) + ' ' +
            'Created: ' + df['created_at'].fillna('').astype(str)
        )
        df['combined_text'] = df['combined_text'].str.strip()
        df = df[df['combined_text'] != '']
        logger.info(f"Preprocessed {len(df)} roles")
        return df
    
    @staticmethod
    def preprocess_product_data_from_csv(df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess product dataset from CSV (original migrate_db.py logic).
        Kept for backward compatibility with CSV imports.
        
        Args:
            df: Raw product DataFrame from CSV
            
        Returns:
            Preprocessed product DataFrame
        """
        logger.info("Preprocessing product data from CSV...")
        
        # Create combined text field for semantic search
        df['combined_text'] = (
            df['title'].str.strip() + ' ' +
            df['description'].str.strip() + ' ' +
            df['main_category'].str.strip() + ' ' +
            df['categories'].str.strip()
        )
        
        # Clean numeric fields
        df['Price'] = pd.to_numeric(df['price'], errors='coerce')
        df['Rating'] = pd.to_numeric(df['average_rating'], errors='coerce')
        df['Rating_Count'] = pd.to_numeric(df['rating_number'], errors='coerce')
        
        # Remove products with invalid prices or ratings
        df = df[df['Price'].notna()]
        df = df[df['Rating'].notna()]
        df = df[df['Price'] > 0]
        df = df[df['Rating'].between(0, 5)]
        
        # Create a unique product ID if not present
        if 'Product_ID' not in df.columns:
            df['Product_ID'] = range(1, len(df) + 1)
        
        # Extract features as a list
        df['feature_list'] = df['features'].apply(lambda x: str(x).split('|') if pd.notnull(x) else [])
        
        # Rename columns to match expected schema
        df = df.rename(columns={
            'title': 'Product_Title',
            'main_category': 'Category',
            'description': 'Description',
            'price': 'Price',
            'average_rating': 'Rating',
            'rating_number': 'Rating_Count',
            'store': 'Store',
            'parent_asin': 'Product_ID'
        })
        
        columns_to_keep = [
            'Product_ID', 'Product_Title', 'Description', 'Category',
            'Price', 'Rating', 'Rating_Count', 'Store', 'feature_list',
            'combined_text'
        ]
        
        df = df[columns_to_keep]
        logger.info(f"Preprocessed {len(df)} products from CSV")
        return df
    
    @staticmethod
    def preprocess_order_data_from_csv(df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess order dataset from CSV (original migrate_db.py logic).
        Kept for backward compatibility with CSV imports.
        
        Args:
            df: Raw order DataFrame from CSV
            
        Returns:
            Preprocessed order DataFrame
        """
        logger.info("Preprocessing order data from CSV...")
        
        # Convert date and time fields
        df['Order_DateTime'] = pd.to_datetime(df['Order_Date'] + ' ' + df['Time'])
        
        # Clean numeric fields
        numeric_columns = ['Sales', 'Quantity', 'Discount', 'Profit', 'Shipping_Cost']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove orders with invalid amounts
        df = df[df['Sales'].notna() & df['Shipping_Cost'].notna()]
        df = df[df['Sales'] > 0]
        
        # Create a unique order ID if not present
        if 'Order_ID' not in df.columns:
            df['Order_ID'] = range(1, len(df) + 1)
        
        # Standardize categorical fields
        df['Order_Priority'] = df['Order_Priority'].str.strip().str.title()
        df['Payment_method'] = df['Payment_method'].str.strip().str.title()
        df['Customer_Login_type'] = df['Customer_Login_type'].str.strip().str.title()
        df['Gender'] = df['Gender'].str.strip().str.title()
        df['Device_Type'] = df['Device_Type'].str.strip().str.title()
        
        # Calculate additional metrics
        df['Total_Amount'] = df['Sales'] * df['Quantity']
        df['Net_Profit'] = df['Profit'] - df['Shipping_Cost']
        
        columns_to_keep = [
            'Order_ID', 'Order_DateTime', 'Customer_Id', 'Gender',
            'Device_Type', 'Customer_Login_type', 'Product_Category',
            'Product', 'Quantity', 'Sales', 'Total_Amount', 'Discount',
            'Profit', 'Net_Profit', 'Shipping_Cost', 'Order_Priority',
            'Payment_method'
        ]
        
        df = df[columns_to_keep]
        logger.info(f"Preprocessed {len(df)} orders from CSV")
        return df
