"""
Cloud Cart Embedding DAG
Generates embeddings for carts table in cloud PostgreSQL.
Schedule: Daily at 6:00 AM (MEDIUM priority)
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
    'cloud_cart_embedding_generation',
    default_args=default_args,
    description='Generate embeddings for cloud carts table',
    schedule_interval=config['schedules']['cart_embedding'],
    catchup=False,
    tags=['cloud', 'embedding', 'carts', 'medium-priority'],
)


def fetch_carts_without_embeddings(**context):
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    query = """
        SELECT id, user_id, status, total_price, created_at, updated_at
        FROM carts
        WHERE embedding IS NULL
        ORDER BY created_at DESC;
    """
    
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        
        carts = [dict(zip(columns, record)) for record in records]
        logger.info(f"Found {len(carts)} carts without embeddings")
        
        context['ti'].xcom_push(key='carts', value=carts)
        return len(carts)
        
    finally:
        cursor.close()
        connection.close()


def process_and_generate_embeddings(**context):
    carts = context['ti'].xcom_pull(key='carts', task_ids='fetch_carts')
    
    if not carts:
        logger.info("No carts to process")
        return 0
    
    df = DataPreprocessor.preprocess_cloud_cart_records(carts)
    
    if df.empty:
        logger.warning("No valid carts after preprocessing")
        return 0
    
    api_key = Variable.get('GOOGLE_API_KEY')
    embedding_generator = EmbeddingGenerator(
        api_key=api_key,
        batch_size=BATCH_SIZE
    )
    
    texts = df['combined_text'].tolist()
    embeddings = embedding_generator.generate_embeddings(texts)
    
    cart_embeddings = []
    for i, row in df.iterrows():
        cart_embeddings.append({
            'id': row['id'],
            'embedding': embeddings[i]
        })
    
    context['ti'].xcom_push(key='cart_embeddings', value=cart_embeddings)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return len(embeddings)


def update_cart_embeddings(**context):
    cart_embeddings = context['ti'].xcom_pull(
        key='cart_embeddings', 
        task_ids='generate_embeddings'
    )
    
    if not cart_embeddings:
        logger.info("No embeddings to update")
        return 0
    
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        update_query = """
            UPDATE carts
            SET embedding = %s::vector
            WHERE id = %s;
        """
        
        for item in cart_embeddings:
            embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'
            cursor.execute(update_query, (embedding_str, item['id']))
        
        connection.commit()
        logger.info(f"Updated {len(cart_embeddings)} cart embeddings")
        return len(cart_embeddings)
        
    except Exception as e:
        connection.rollback()
        logger.error(f"Error updating embeddings: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()


fetch_task = PythonOperator(
    task_id='fetch_carts',
    python_callable=fetch_carts_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_cart_embeddings,
    dag=dag,
)

fetch_task >> generate_task >> update_task
