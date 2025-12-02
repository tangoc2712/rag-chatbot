"""
Cloud Payment Embedding DAG
Generates embeddings for payments table in cloud PostgreSQL.
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
    'cloud_payment_embedding_generation',
    default_args=default_args,
    description='Generate embeddings for cloud payments table',
    schedule_interval=config['schedules']['payment_embedding'],
    catchup=False,
    tags=['cloud', 'embedding', 'payments', 'medium-priority'],
)


def fetch_payments_without_embeddings(**context):
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    query = """
        SELECT payment_id, order_id, method, amount, status, paid_at
        FROM payment
        WHERE embedding IS NULL
        ORDER BY paid_at DESC;
    """
    
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        
        payments = [dict(zip(columns, record)) for record in records]
        logger.info(f"Found {len(payments)} payments without embeddings")
        
        context['ti'].xcom_push(key='payments', value=payments)
        return len(payments)
        
    finally:
        cursor.close()
        connection.close()


def process_and_generate_embeddings(**context):
    payments = context['ti'].xcom_pull(key='payments', task_ids='fetch_payments')
    
    if not payments:
        logger.info("No payments to process")
        return 0
    
    df = DataPreprocessor.preprocess_cloud_payment_records(payments)
    
    if df.empty:
        logger.warning("No valid payments after preprocessing")
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
    
    payment_embeddings = []
    for i, row in df.iterrows():
        payment_embeddings.append({
            'payment_id': row['payment_id'],
            'embedding': embeddings[i]
        })
    
    context['ti'].xcom_push(key='payment_embeddings', value=payment_embeddings)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return len(embeddings)


def update_payment_embeddings(**context):
    payment_embeddings = context['ti'].xcom_pull(
        key='payment_embeddings', 
        task_ids='generate_embeddings'
    )
    
    if not payment_embeddings:
        logger.info("No embeddings to update")
        return 0
    
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        update_query = """
            UPDATE payment
            SET embedding = %s::vector
            WHERE payment_id = %s;
        """
        
        for item in payment_embeddings:
            embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'
            cursor.execute(update_query, (embedding_str, item['payment_id']))
        
        connection.commit()
        logger.info(f"Updated {len(payment_embeddings)} payment embeddings")
        return len(payment_embeddings)
        
    except Exception as e:
        connection.rollback()
        logger.error(f"Error updating embeddings: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()


fetch_task = PythonOperator(
    task_id='fetch_payments',
    python_callable=fetch_payments_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_payment_embeddings,
    dag=dag,
)

fetch_task >> generate_task >> update_task
