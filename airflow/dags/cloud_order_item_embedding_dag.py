"""
Cloud Order Item Embedding DAG
Generates embeddings for order_items table in cloud PostgreSQL.
Schedule: Daily at 5:00 AM (MEDIUM priority)
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
import json
import logging

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
    'cloud_order_item_embedding_generation',
    default_args=default_args,
    description='Generate embeddings for cloud order_items table',
    schedule_interval=config['schedules']['order_item_embedding'],
    catchup=False,
    tags=['cloud', 'embedding', 'order-items', 'medium-priority'],
)


def fetch_order_items_without_embeddings(**context):
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    query = """
        SELECT order_item_id, order_id, product_id, quantity, unit_price, total_price
        FROM order_items
        WHERE embedding IS NULL
        ORDER BY order_item_id DESC;
    """
    
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        
        order_items = [dict(zip(columns, record)) for record in records]
        logger.info(f"Found {len(order_items)} order items without embeddings")
        
        context['ti'].xcom_push(key='order_items', value=order_items)
        return len(order_items)
        
    finally:
        cursor.close()
        connection.close()


def process_and_generate_embeddings(**context):
    order_items = context['ti'].xcom_pull(key='order_items', task_ids='fetch_order_items')
    
    if not order_items:
        logger.info("No order items to process")
        return 0
    
    df = DataPreprocessor.preprocess_cloud_order_item_records(order_items)
    
    if df.empty:
        logger.warning("No valid order items after preprocessing")
        return 0
    
    api_key = Variable.get('GOOGLE_API_KEY')
    embedding_generator = EmbeddingGenerator(
        api_key=api_key,
        batch_size=BATCH_SIZE
    )
    
    texts = df['combined_text'].tolist()
    embeddings = embedding_generator.generate_embeddings(texts)
    
    order_item_embeddings = []
    for i, row in df.iterrows():
        order_item_embeddings.append({
            'order_item_id': row['order_item_id'],
            'embedding': embeddings[i]
        })
    
    context['ti'].xcom_push(key='order_item_embeddings', value=order_item_embeddings)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return len(embeddings)


def update_order_item_embeddings(**context):
    order_item_embeddings = context['ti'].xcom_pull(
        key='order_item_embeddings', 
        task_ids='generate_embeddings'
    )
    
    if not order_item_embeddings:
        logger.info("No embeddings to update")
        return 0
    
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        update_query = """
            UPDATE order_items
            SET embedding = %s::vector
            WHERE order_item_id = %s;
        """
        
        for item in order_item_embeddings:
            embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'
            cursor.execute(update_query, (embedding_str, item['order_item_id']))
        
        connection.commit()
        logger.info(f"Updated {len(order_item_embeddings)} order item embeddings")
        return len(order_item_embeddings)
        
    except Exception as e:
        connection.rollback()
        logger.error(f"Error updating embeddings: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()


fetch_task = PythonOperator(
    task_id='fetch_order_items',
    python_callable=fetch_order_items_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_order_item_embeddings,
    dag=dag,
)

fetch_task >> generate_task >> update_task
