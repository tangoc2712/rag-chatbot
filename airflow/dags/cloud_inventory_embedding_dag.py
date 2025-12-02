"""
Cloud Inventory Embedding DAG
Generates embeddings for inventory table in cloud PostgreSQL.
Schedule: Daily at 6:00 AM (MEDIUM priority)
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
    'cloud_inventory_embedding_generation',
    default_args=default_args,
    description='Generate embeddings for cloud inventory table',
    schedule_interval=config['schedules']['inventory_embedding'],
    catchup=False,
    tags=['cloud', 'embedding', 'inventory', 'medium-priority'],
)


def fetch_inventory_without_embeddings(**context):
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    query = """
        SELECT inventory_id, product_id, warehouse_id, quantity, last_updated
        FROM inventory
        WHERE embedding IS NULL
        ORDER BY last_updated DESC;
    """
    
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        
        inventory = [dict(zip(columns, record)) for record in records]
        logger.info(f"Found {len(inventory)} inventory records without embeddings")
        
        context['ti'].xcom_push(key='inventory', value=inventory)
        return len(inventory)
        
    finally:
        cursor.close()
        connection.close()


def process_and_generate_embeddings(**context):
    inventory = context['ti'].xcom_pull(key='inventory', task_ids='fetch_inventory')
    
    if not inventory:
        logger.info("No inventory to process")
        return 0
    
    df = DataPreprocessor.preprocess_cloud_inventory_records(inventory)
    
    if df.empty:
        logger.warning("No valid inventory after preprocessing")
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
    
    inventory_embeddings = []
    for i, row in df.iterrows():
        inventory_embeddings.append({
            'inventory_id': row['inventory_id'],
            'embedding': embeddings[i]
        })
    
    context['ti'].xcom_push(key='inventory_embeddings', value=inventory_embeddings)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return len(embeddings)


def update_inventory_embeddings(**context):
    inventory_embeddings = context['ti'].xcom_pull(
        key='inventory_embeddings', 
        task_ids='generate_embeddings'
    )
    
    if not inventory_embeddings:
        logger.info("No embeddings to update")
        return 0
    
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        update_query = """
            UPDATE inventory
            SET embedding = %s::vector
            WHERE inventory_id = %s;
        """
        
        for item in inventory_embeddings:
            embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'
            cursor.execute(update_query, (embedding_str, item['inventory_id']))
        
        connection.commit()
        logger.info(f"Updated {len(inventory_embeddings)} inventory embeddings")
        return len(inventory_embeddings)
        
    except Exception as e:
        connection.rollback()
        logger.error(f"Error updating embeddings: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()


fetch_task = PythonOperator(
    task_id='fetch_inventory',
    python_callable=fetch_inventory_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_inventory_embeddings,
    dag=dag,
)

fetch_task >> generate_task >> update_task
