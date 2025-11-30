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
