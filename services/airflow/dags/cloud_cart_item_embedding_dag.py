"""
Cloud Cart Item Embedding DAG
Generates embeddings for cart_items table in cloud PostgreSQL.
Schedule: Daily at 7:00 AM (LOW priority)
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
    'cloud_cart_item_embedding_generation',
    default_args=default_args,
    description='Generate embeddings for cloud cart_items table',
    schedule_interval=config['schedules']['cart_item_embedding'],
    catchup=False,
    tags=['cloud', 'embedding', 'cart-items', 'low-priority'],
)


def fetch_cart_items_without_embeddings(**context):
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    query = """
        SELECT cart_item_id, cart_id, product_id, quantity, unit_price, total_price, created_at
        FROM cart_item
        WHERE embedding IS NULL
        ORDER BY created_at DESC;
    """
    
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        
        cart_items = [dict(zip(columns, record)) for record in records]
        logger.info(f"Found {len(cart_items)} cart items without embeddings")
        
        context['ti'].xcom_push(key='cart_items', value=cart_items)
        return len(cart_items)
        
    finally:
        cursor.close()
        connection.close()


def process_and_generate_embeddings(**context):
    cart_items = context['ti'].xcom_pull(key='cart_items', task_ids='fetch_cart_items')
    
    if not cart_items:
        logger.info("No cart items to process")
        return 0
    
    df = DataPreprocessor.preprocess_cloud_cart_item_records(cart_items)
    
    if df.empty:
        logger.warning("No valid cart items after preprocessing")
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
    
    cart_item_embeddings = []
    for i, row in df.iterrows():
        cart_item_embeddings.append({
            'cart_item_id': row['cart_item_id'],
            'embedding': embeddings[i]
        })
    
    context['ti'].xcom_push(key='cart_item_embeddings', value=cart_item_embeddings)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return len(embeddings)


def update_cart_item_embeddings(**context):
    cart_item_embeddings = context['ti'].xcom_pull(
        key='cart_item_embeddings', 
        task_ids='generate_embeddings'
    )
    
    if not cart_item_embeddings:
        logger.info("No embeddings to update")
        return 0
    
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        update_query = """
            UPDATE cart_item
            SET embedding = %s::vector
            WHERE cart_item_id = %s;
        """
        
        for item in cart_item_embeddings:
            embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'
            cursor.execute(update_query, (embedding_str, item['cart_item_id']))
        
        connection.commit()
        logger.info(f"Updated {len(cart_item_embeddings)} cart item embeddings")
        return len(cart_item_embeddings)
        
    except Exception as e:
        connection.rollback()
        logger.error(f"Error updating embeddings: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()


fetch_task = PythonOperator(
    task_id='fetch_cart_items',
    python_callable=fetch_cart_items_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_cart_item_embeddings,
    dag=dag,
)

fetch_task >> generate_task >> update_task
