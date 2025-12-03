"""
Cloud Shipment Embedding DAG
Generates embeddings for shipments table in cloud PostgreSQL.
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
    'cloud_shipment_embedding_generation',
    default_args=default_args,
    description='Generate embeddings for cloud shipments table',
    schedule_interval=config['schedules']['shipment_embedding'],
    catchup=False,
    tags=['cloud', 'embedding', 'shipments', 'medium-priority'],
)


def fetch_shipments_without_embeddings(**context):
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    query = """
        SELECT shipment_id, order_id, tracking_number, status, 
               shipped_at, delivered_at, carrier_id
        FROM shipment
        WHERE embedding IS NULL
        ORDER BY shipped_at DESC;
    """
    
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        
        shipments = [dict(zip(columns, record)) for record in records]
        logger.info(f"Found {len(shipments)} shipments without embeddings")
        
        context['ti'].xcom_push(key='shipments', value=shipments)
        return len(shipments)
        
    finally:
        cursor.close()
        connection.close()


def process_and_generate_embeddings(**context):
    shipments = context['ti'].xcom_pull(key='shipments', task_ids='fetch_shipments')
    
    if not shipments:
        logger.info("No shipments to process")
        return 0
    
    df = DataPreprocessor.preprocess_cloud_shipment_records(shipments)
    
    if df.empty:
        logger.warning("No valid shipments after preprocessing")
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
    
    shipment_embeddings = []
    for i, row in df.iterrows():
        shipment_embeddings.append({
            'shipment_id': row['shipment_id'],
            'embedding': embeddings[i]
        })
    
    context['ti'].xcom_push(key='shipment_embeddings', value=shipment_embeddings)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return len(embeddings)


def update_shipment_embeddings(**context):
    shipment_embeddings = context['ti'].xcom_pull(
        key='shipment_embeddings', 
        task_ids='generate_embeddings'
    )
    
    if not shipment_embeddings:
        logger.info("No embeddings to update")
        return 0
    
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        update_query = """
            UPDATE shipment
            SET embedding = %s::vector
            WHERE shipment_id = %s;
        """
        
        for item in shipment_embeddings:
            embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'
            cursor.execute(update_query, (embedding_str, item['shipment_id']))
        
        connection.commit()
        logger.info(f"Updated {len(shipment_embeddings)} shipment embeddings")
        return len(shipment_embeddings)
        
    except Exception as e:
        connection.rollback()
        logger.error(f"Error updating embeddings: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()


fetch_task = PythonOperator(
    task_id='fetch_shipments',
    python_callable=fetch_shipments_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_shipment_embeddings,
    dag=dag,
)

fetch_task >> generate_task >> update_task
