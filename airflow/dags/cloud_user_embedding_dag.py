"""
Cloud User Embedding DAG
Generates embeddings for users table in cloud PostgreSQL.
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
    'cloud_user_embedding_generation',
    default_args=default_args,
    description='Generate embeddings for cloud users table',
    schedule_interval=config['schedules']['user_embedding'],
    catchup=False,
    tags=['cloud', 'embedding', 'users', 'medium-priority'],
)


def fetch_users_without_embeddings(**context):
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    query = """
        SELECT user_id, email, full_name, phone, address, date_of_birth, 
               job, gender, role_id, created_at, updated_at, is_active
        FROM users
        WHERE embedding IS NULL
        ORDER BY created_at DESC;
    """
    
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        
        users = [dict(zip(columns, record)) for record in records]
        logger.info(f"Found {len(users)} users without embeddings")
        
        context['ti'].xcom_push(key='users', value=users)
        return len(users)
        
    finally:
        cursor.close()
        connection.close()


def process_and_generate_embeddings(**context):
    users = context['ti'].xcom_pull(key='users', task_ids='fetch_users')
    
    if not users:
        logger.info("No users to process")
        return 0
    
    df = DataPreprocessor.preprocess_cloud_user_records(users)
    
    if df.empty:
        logger.warning("No valid users after preprocessing")
        return 0
    
    api_key = Variable.get('GOOGLE_API_KEY')
    embedding_generator = EmbeddingGenerator(
        api_key=api_key,
        batch_size=BATCH_SIZE
    )
    
    texts = df['combined_text'].tolist()
    embeddings = embedding_generator.generate_embeddings(texts)
    
    user_embeddings = []
    for i, row in df.iterrows():
        user_embeddings.append({
            'user_id': row['user_id'],
            'embedding': embeddings[i]
        })
    
    context['ti'].xcom_push(key='user_embeddings', value=user_embeddings)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return len(embeddings)


def update_user_embeddings(**context):
    user_embeddings = context['ti'].xcom_pull(
        key='user_embeddings', 
        task_ids='generate_embeddings'
    )
    
    if not user_embeddings:
        logger.info("No embeddings to update")
        return 0
    
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        update_query = """
            UPDATE users
            SET embedding = %s::vector
            WHERE user_id = %s;
        """
        
        for item in user_embeddings:
            embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'
            cursor.execute(update_query, (embedding_str, item['user_id']))
        
        connection.commit()
        logger.info(f"Updated {len(user_embeddings)} user embeddings")
        return len(user_embeddings)
        
    except Exception as e:
        connection.rollback()
        logger.error(f"Error updating embeddings: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()


fetch_task = PythonOperator(
    task_id='fetch_users',
    python_callable=fetch_users_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_user_embeddings,
    dag=dag,
)

fetch_task >> generate_task >> update_task
