"""
Airflow DAG for daily order embedding generation.
Processes orders with NULL embeddings and updates the database.
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
    'order_embedding_generation',
    default_args=default_args,
    description='Daily generation of embeddings for orders with NULL embeddings',
    schedule_interval='0 3 * * *',  # Daily at 3 AM
    catchup=False,
    tags=['embeddings', 'orders', 'rag'],
)


def fetch_orders_without_embeddings(**context):
    """
    Fetch orders that have NULL embeddings from PostgreSQL.
    
    Returns:
        List of order records
    """
    logger.info("Fetching orders without embeddings...")
    
    # Get PostgreSQL connection
    pg_hook = PostgresHook(postgres_conn_id='postgres_ecommerce_rag')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()
    
    try:
        # Query orders with NULL embeddings
        cursor.execute("""
            SELECT 
                order_id,
                order_datetime,
                customer_id,
                gender,
                device_type,
                customer_login_type,
                product_category,
                product,
                quantity,
                sales,
                total_amount,
                discount,
                profit,
                net_profit,
                shipping_cost,
                order_priority,
                payment_method
            FROM orders
            WHERE embedding IS NULL
            ORDER BY order_id
        """)
        
        columns = [desc[0] for desc in cursor.description]
        records = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        logger.info(f"Found {len(records)} orders without embeddings")
        
        # Push to XCom for next task
        context['task_instance'].xcom_push(key='orders_count', value=len(records))
        
        return records
        
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def process_and_generate_embeddings(**context):
    """
    Preprocess orders and generate embeddings using Gemini API.
    
    Returns:
        List of tuples (order_id, embedding_vector)
    """
    # Get orders from previous task
    task_instance = context['task_instance']
    orders = task_instance.xcom_pull(task_ids='fetch_orders')
    
    if not orders:
        logger.info("No orders to process")
        return []
    
    logger.info(f"Processing {len(orders)} orders")
    
    # Preprocess orders
    preprocessor = DataPreprocessor()
    df = preprocessor.preprocess_order_records(orders)
    
    if df.empty:
        logger.warning("No valid orders after preprocessing")
        return []
    
    # Get Google API key from Airflow Variables
    google_api_key = Variable.get('GOOGLE_API_KEY')
    
    # Generate embeddings
    embedding_gen = EmbeddingGenerator(api_key=google_api_key, batch_size=100)
    embeddings = embedding_gen.generate_embeddings(df['embedding_text'].tolist())
    
    # Combine order IDs with embeddings
    results = []
    for idx, (_, row) in enumerate(df.iterrows()):
        results.append((row['order_id'], embeddings[idx]))
    
    logger.info(f"Generated embeddings for {len(results)} orders")
    
    # Push count to XCom
    task_instance.xcom_push(key='embeddings_generated', value=len(results))
    
    return results


def update_order_embeddings(**context):
    """
    Update orders table with generated embeddings.
    """
    # Get embeddings from previous task
    task_instance = context['task_instance']
    embeddings_data = task_instance.xcom_pull(task_ids='generate_embeddings')
    
    if not embeddings_data:
        logger.info("No embeddings to update")
        return
    
    logger.info(f"Updating {len(embeddings_data)} order embeddings")
    
    # Get PostgreSQL connection
    pg_hook = PostgresHook(postgres_conn_id='postgres_ecommerce_rag')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()
    
    try:
        updated_count = 0
        
        for order_id, embedding in embeddings_data:
            cursor.execute("""
                UPDATE orders
                SET embedding = %s::vector
                WHERE order_id = %s
            """, (embedding, order_id))
            updated_count += cursor.rowcount
        
        conn.commit()
        logger.info(f"Successfully updated {updated_count} order embeddings")
        
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
    
    orders_count = task_instance.xcom_pull(task_ids='fetch_orders', key='orders_count') or 0
    embeddings_generated = task_instance.xcom_pull(task_ids='generate_embeddings', key='embeddings_generated') or 0
    updated_count = task_instance.xcom_pull(task_ids='update_embeddings', key='updated_count') or 0
    
    logger.info("=" * 60)
    logger.info("ORDER EMBEDDING GENERATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Orders found without embeddings: {orders_count}")
    logger.info(f"Embeddings generated: {embeddings_generated}")
    logger.info(f"Database records updated: {updated_count}")
    logger.info("=" * 60)


# Define tasks
fetch_task = PythonOperator(
    task_id='fetch_orders',
    python_callable=fetch_orders_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_order_embeddings,
    dag=dag,
)

summary_task = PythonOperator(
    task_id='log_summary',
    python_callable=log_summary,
    dag=dag,
)

# Define task dependencies
fetch_task >> generate_task >> update_task >> summary_task
