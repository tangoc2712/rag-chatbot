"""
Cloud Order Embedding DAG
Generates embeddings for orders table in cloud PostgreSQL.
Schedule: Daily at 4:00 AM (HIGH priority)
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
import json
import logging
import tiktoken

from utils.embedding_generator import EmbeddingGenerator
from utils.data_preprocessor import DataPreprocessor

config = json.loads(Variable.get('stg_config'))
POSTGRES_CONN_ID = config['postgres']['conn_id']
BATCH_SIZE = config['embedding']['batch_size']
RATE_LIMIT = config['embedding']['rate_limit_seconds']

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'cloud_order_embedding_generation',
    default_args=default_args,
    description='Generate embeddings for cloud orders table',
    schedule_interval=config['schedules']['order_embedding'],
    catchup=False,
    tags=['cloud', 'embedding', 'orders', 'high-priority'],
)


def fetch_orders_without_embeddings(**context):
    """Fetch orders that don't have embeddings yet."""
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    query = """
        SELECT order_id, user_id, status, order_total, currency, 
               created_at, updated_at
        FROM "order"
        WHERE embedding IS NULL
        ORDER BY created_at DESC;
    """
    
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        
        orders = [dict(zip(columns, record)) for record in records]
        logger.info(f"Found {len(orders)} orders without embeddings")
        
        context['ti'].xcom_push(key='orders', value=orders)
        return len(orders)
        
    finally:
        cursor.close()
        connection.close()


def process_and_generate_embeddings(**context):
    """Preprocess orders and generate embeddings."""
    orders = context['ti'].xcom_pull(key='orders', task_ids='fetch_orders')
    
    if not orders:
        logger.info("No orders to process")
        return 0
    
    df = DataPreprocessor.preprocess_cloud_order_records(orders)
    
    if df.empty:
        logger.warning("No valid orders after preprocessing")
        return 0
    
    api_key = Variable.get('GOOGLE_API_KEY')
    embedding_generator = EmbeddingGenerator(
        api_key=api_key,
        batch_size=BATCH_SIZE
    )
    
    texts = df['combined_text'].tolist()
    
    # Count tokens using tiktoken
    encoding = tiktoken.get_encoding("cl100k_base")
    total_tokens = sum(len(encoding.encode(text)) for text in texts)
    logger.info(f"Token count before embedding: {total_tokens} tokens for {len(texts)} texts")
    
    embeddings = embedding_generator.generate_embeddings(texts)
    
    order_embeddings = []
    for i, row in df.iterrows():
        order_embeddings.append({
            'order_id': row['order_id'],
            'embedding': embeddings[i]
        })
    
    context['ti'].xcom_push(key='order_embeddings', value=order_embeddings)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return len(embeddings)


def update_order_embeddings(**context):
    """Update orders table with generated embeddings."""
    order_embeddings = context['ti'].xcom_pull(
        key='order_embeddings', 
        task_ids='generate_embeddings'
    )
    
    if not order_embeddings:
        logger.info("No embeddings to update")
        return 0
    
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        update_query = """
            UPDATE "order"
            SET embedding = %s::vector
            WHERE order_id = %s;
        """
        
        for item in order_embeddings:
            embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'
            cursor.execute(update_query, (embedding_str, item['order_id']))
        
        connection.commit()
        logger.info(f"Updated {len(order_embeddings)} order embeddings")
        return len(order_embeddings)
        
    except Exception as e:
        connection.rollback()
        logger.error(f"Error updating embeddings: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()


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

fetch_task >> generate_task >> update_task
