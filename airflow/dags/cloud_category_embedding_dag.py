"""
Cloud Category Embedding DAG
Generates embeddings for categories table in cloud PostgreSQL.
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
    'cloud_category_embedding_generation',
    default_args=default_args,
    description='Generate embeddings for cloud categories table',
    schedule_interval=config['schedules']['category_embedding'],
    catchup=False,
    tags=['cloud', 'embedding', 'categories', 'medium-priority'],
)


def fetch_categories_without_embeddings(**context):
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    query = """
        SELECT category_id, name, type, parent_category_id
        FROM categories
        WHERE embedding IS NULL
        ORDER BY category_id DESC;
    """
    
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        
        categories = [dict(zip(columns, record)) for record in records]
        logger.info(f"Found {len(categories)} categories without embeddings")
        
        context['ti'].xcom_push(key='categories', value=categories)
        return len(categories)
        
    finally:
        cursor.close()
        connection.close()


def process_and_generate_embeddings(**context):
    categories = context['ti'].xcom_pull(key='categories', task_ids='fetch_categories')
    
    if not categories:
        logger.info("No categories to process")
        return 0
    
    df = DataPreprocessor.preprocess_cloud_category_records(categories)
    
    if df.empty:
        logger.warning("No valid categories after preprocessing")
        return 0
    
    api_key = Variable.get('GOOGLE_API_KEY')
    embedding_generator = EmbeddingGenerator(
        api_key=api_key,
        batch_size=BATCH_SIZE
    )
    
    texts = df['combined_text'].tolist()
    embeddings = embedding_generator.generate_embeddings(texts)
    
    category_embeddings = []
    for i, row in df.iterrows():
        category_embeddings.append({
            'category_id': row['category_id'],
            'embedding': embeddings[i]
        })
    
    context['ti'].xcom_push(key='category_embeddings', value=category_embeddings)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return len(embeddings)


def update_category_embeddings(**context):
    category_embeddings = context['ti'].xcom_pull(
        key='category_embeddings', 
        task_ids='generate_embeddings'
    )
    
    if not category_embeddings:
        logger.info("No embeddings to update")
        return 0
    
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        update_query = """
            UPDATE categories
            SET embedding = %s::vector
            WHERE category_id = %s;
        """
        
        for item in category_embeddings:
            embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'
            cursor.execute(update_query, (embedding_str, item['category_id']))
        
        connection.commit()
        logger.info(f"Updated {len(category_embeddings)} category embeddings")
        return len(category_embeddings)
        
    except Exception as e:
        connection.rollback()
        logger.error(f"Error updating embeddings: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()


fetch_task = PythonOperator(
    task_id='fetch_categories',
    python_callable=fetch_categories_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_category_embeddings,
    dag=dag,
)

fetch_task >> generate_task >> update_task
