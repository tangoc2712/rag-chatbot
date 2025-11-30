"""
Cloud Role Embedding DAG
Generates embeddings for roles table in cloud PostgreSQL.
Schedule: Daily at 7:00 AM (LOW priority)
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
    'cloud_role_embedding_generation',
    default_args=default_args,
    description='Generate embeddings for cloud roles table',
    schedule_interval=config['schedules']['role_embedding'],
    catchup=False,
    tags=['cloud', 'embedding', 'roles', 'low-priority'],
)


def fetch_roles_without_embeddings(**context):
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    query = """
        SELECT role_id, role_name, is_active, created_at, updated_at
        FROM roles
        WHERE embedding IS NULL
        ORDER BY created_at DESC;
    """
    
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        
        roles = [dict(zip(columns, record)) for record in records]
        logger.info(f"Found {len(roles)} roles without embeddings")
        
        context['ti'].xcom_push(key='roles', value=roles)
        return len(roles)
        
    finally:
        cursor.close()
        connection.close()


def process_and_generate_embeddings(**context):
    roles = context['ti'].xcom_pull(key='roles', task_ids='fetch_roles')
    
    if not roles:
        logger.info("No roles to process")
        return 0
    
    df = DataPreprocessor.preprocess_cloud_role_records(roles)
    
    if df.empty:
        logger.warning("No valid roles after preprocessing")
        return 0
    
    api_key = Variable.get('GOOGLE_API_KEY')
    embedding_generator = EmbeddingGenerator(
        api_key=api_key,
        batch_size=BATCH_SIZE
    )
    
    texts = df['combined_text'].tolist()
    embeddings = embedding_generator.generate_embeddings(texts)
    
    role_embeddings = []
    for i, row in df.iterrows():
        role_embeddings.append({
            'role_id': row['role_id'],
            'embedding': embeddings[i]
        })
    
    context['ti'].xcom_push(key='role_embeddings', value=role_embeddings)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return len(embeddings)


def update_role_embeddings(**context):
    role_embeddings = context['ti'].xcom_pull(
        key='role_embeddings', 
        task_ids='generate_embeddings'
    )
    
    if not role_embeddings:
        logger.info("No embeddings to update")
        return 0
    
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        update_query = """
            UPDATE roles
            SET embedding = %s::vector
            WHERE role_id = %s;
        """
        
        for item in role_embeddings:
            embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'
            cursor.execute(update_query, (embedding_str, item['role_id']))
        
        connection.commit()
        logger.info(f"Updated {len(role_embeddings)} role embeddings")
        return len(role_embeddings)
        
    except Exception as e:
        connection.rollback()
        logger.error(f"Error updating embeddings: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()


fetch_task = PythonOperator(
    task_id='fetch_roles',
    python_callable=fetch_roles_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_role_embeddings,
    dag=dag,
)

fetch_task >> generate_task >> update_task
