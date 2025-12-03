"""
Airflow DAG for daily product embedding generation.
Processes products with NULL embeddings and updates the database.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
import logging
import sys
from pathlib import Path

# Add utils to path
sys.path.append(str(Path(__file__).parent))
from utils.embedding_generator import EmbeddingGenerator
from utils.data_preprocessor import DataPreprocessor

logger = logging.getLogger(__name__)

# Default DAG arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 30),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'product_embedding_generation',
    default_args=default_args,
    description='Daily generation of embeddings for products with NULL embeddings',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    catchup=False,
    tags=['embeddings', 'products', 'rag'],
)


def fetch_products_without_embeddings(**context):
    """
    Fetch products that have NULL embeddings from PostgreSQL.
    
    Returns:
        List of product records
    """
    logger.info("Fetching products without embeddings...")
    
    # Get PostgreSQL connection
    pg_hook = PostgresHook(postgres_conn_id='postgres_ecommerce_rag')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()
    
    try:
        # Query products with NULL embeddings
        cursor.execute("""
            SELECT 
                product_id,
                product_title,
                description,
                category,
                price,
                rating,
                rating_count,
                store,
                feature_list,
                combined_text
            FROM products
            WHERE embedding IS NULL
            ORDER BY product_id
        """)
        
        columns = [desc[0] for desc in cursor.description]
        records = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        logger.info(f"Found {len(records)} products without embeddings")
        
        # Push to XCom for next task
        context['task_instance'].xcom_push(key='products_count', value=len(records))
        
        return records
        
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def process_and_generate_embeddings(**context):
    """
    Preprocess products and generate embeddings using Gemini API.
    
    Returns:
        List of tuples (product_id, embedding_vector)
    """
    # Get products from previous task
    task_instance = context['task_instance']
    products = task_instance.xcom_pull(task_ids='fetch_products')
    
    if not products:
        logger.info("No products to process")
        return []
    
    logger.info(f"Processing {len(products)} products")
    
    # Preprocess products
    preprocessor = DataPreprocessor()
    df = preprocessor.preprocess_product_records(products)
    
    if df.empty:
        logger.warning("No valid products after preprocessing")
        return []
    
    # Get Google API key from Airflow Variables
    google_api_key = Variable.get('GOOGLE_API_KEY')
    
    # Generate embeddings
    embedding_gen = EmbeddingGenerator(api_key=google_api_key, batch_size=100)
    embeddings = embedding_gen.generate_embeddings(df['combined_text'].tolist())
    
    # Combine product IDs with embeddings
    results = []
    for idx, (_, row) in enumerate(df.iterrows()):
        results.append((row['product_id'], embeddings[idx]))
    
    logger.info(f"Generated embeddings for {len(results)} products")
    
    # Push count to XCom
    task_instance.xcom_push(key='embeddings_generated', value=len(results))
    
    return results


def update_product_embeddings(**context):
    """
    Update products table with generated embeddings.
    """
    # Get embeddings from previous task
    task_instance = context['task_instance']
    embeddings_data = task_instance.xcom_pull(task_ids='generate_embeddings')
    
    if not embeddings_data:
        logger.info("No embeddings to update")
        return
    
    logger.info(f"Updating {len(embeddings_data)} product embeddings")
    
    # Get PostgreSQL connection
    pg_hook = PostgresHook(postgres_conn_id='postgres_ecommerce_rag')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()
    
    try:
        updated_count = 0
        
        for product_id, embedding in embeddings_data:
            cursor.execute("""
                UPDATE products
                SET embedding = %s::vector
                WHERE product_id = %s
            """, (embedding, product_id))
            updated_count += cursor.rowcount
        
        conn.commit()
        logger.info(f"Successfully updated {updated_count} product embeddings")
        
        # Push final count to XCom
        task_instance.xcom_push(key='updated_count', value=updated_count)
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating embeddings: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def log_summary(**context):
    """
    Log summary statistics of the embedding generation run.
    """
    task_instance = context['task_instance']
    
    products_count = task_instance.xcom_pull(task_ids='fetch_products', key='products_count') or 0
    embeddings_generated = task_instance.xcom_pull(task_ids='generate_embeddings', key='embeddings_generated') or 0
    updated_count = task_instance.xcom_pull(task_ids='update_embeddings', key='updated_count') or 0
    
    logger.info("=" * 60)
    logger.info("PRODUCT EMBEDDING GENERATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Products found without embeddings: {products_count}")
    logger.info(f"Embeddings generated: {embeddings_generated}")
    logger.info(f"Database records updated: {updated_count}")
    logger.info("=" * 60)


# Define tasks
fetch_task = PythonOperator(
    task_id='fetch_products',
    python_callable=fetch_products_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_product_embeddings,
    dag=dag,
)

summary_task = PythonOperator(
    task_id='log_summary',
    python_callable=log_summary,
    dag=dag,
)

# Define task dependencies
fetch_task >> generate_task >> update_task >> summary_task
