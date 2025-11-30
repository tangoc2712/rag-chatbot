"""
Cloud Event Embedding DAG
Generates embeddings for events table in cloud PostgreSQL.
Schedule: Daily at 4:00 AM (HIGH priority)
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
    'cloud_event_embedding_generation',
    default_args=default_args,
    description='Generate embeddings for cloud events table',
    schedule_interval=config['schedules']['event_embedding'],
    catchup=False,
    tags=['cloud', 'embedding', 'events', 'high-priority'],
)


def fetch_events_without_embeddings(**context):
    """Fetch events that don't have embeddings yet."""
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    query = """
        SELECT event_id, user_id, session_id, event_type, metadata, ts
        FROM events
        WHERE embedding IS NULL
        ORDER BY ts DESC;
    """
    
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        
        events = [dict(zip(columns, record)) for record in records]
        logger.info(f"Found {len(events)} events without embeddings")
        
        context['ti'].xcom_push(key='events', value=events)
        return len(events)
        
    finally:
        cursor.close()
        connection.close()


def process_and_generate_embeddings(**context):
    """Preprocess events and generate embeddings."""
    events = context['ti'].xcom_pull(key='events', task_ids='fetch_events')
    
    if not events:
        logger.info("No events to process")
        return 0
    
    df = DataPreprocessor.preprocess_cloud_event_records(events)
    
    if df.empty:
        logger.warning("No valid events after preprocessing")
        return 0
    
    api_key = Variable.get('GOOGLE_API_KEY')
    embedding_generator = EmbeddingGenerator(
        api_key=api_key,
        batch_size=BATCH_SIZE
    )
    
    texts = df['combined_text'].tolist()
    embeddings = embedding_generator.generate_embeddings(texts)
    
    event_embeddings = []
    for i, row in df.iterrows():
        event_embeddings.append({
            'event_id': row['event_id'],
            'embedding': embeddings[i]
        })
    
    context['ti'].xcom_push(key='event_embeddings', value=event_embeddings)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return len(embeddings)


def update_event_embeddings(**context):
    """Update events table with generated embeddings."""
    event_embeddings = context['ti'].xcom_pull(
        key='event_embeddings', 
        task_ids='generate_embeddings'
    )
    
    if not event_embeddings:
        logger.info("No embeddings to update")
        return 0
    
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        update_query = """
            UPDATE events
            SET embedding = %s::vector
            WHERE event_id = %s;
        """
        
        for item in event_embeddings:
            embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'
            cursor.execute(update_query, (embedding_str, item['event_id']))
        
        connection.commit()
        logger.info(f"Updated {len(event_embeddings)} event embeddings")
        return len(event_embeddings)
        
    except Exception as e:
        connection.rollback()
        logger.error(f"Error updating embeddings: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()


fetch_task = PythonOperator(
    task_id='fetch_events',
    python_callable=fetch_events_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_event_embeddings,
    dag=dag,
)

fetch_task >> generate_task >> update_task
