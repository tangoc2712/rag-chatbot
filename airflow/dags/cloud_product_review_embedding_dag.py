"""
Cloud Product Review Embedding DAG
Generates embeddings for product_reviews table in cloud PostgreSQL.
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
    'cloud_product_review_embedding_generation',
    default_args=default_args,
    description='Generate embeddings for cloud product_reviews table',
    schedule_interval=config['schedules']['product_review_embedding'],
    catchup=False,
    tags=['cloud', 'embedding', 'product-reviews', 'high-priority'],
)


def fetch_reviews_without_embeddings(**context):
    """Fetch product reviews that don't have embeddings yet."""
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    query = """
        SELECT review_id, product_id, user_id, rating, review_text, 
               review_date, helpful_count
        FROM product_reviews
        WHERE embedding IS NULL
        ORDER BY review_date DESC;
    """
    
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        
        reviews = [dict(zip(columns, record)) for record in records]
        logger.info(f"Found {len(reviews)} reviews without embeddings")
        
        context['ti'].xcom_push(key='reviews', value=reviews)
        return len(reviews)
        
    finally:
        cursor.close()
        connection.close()


def process_and_generate_embeddings(**context):
    """Preprocess reviews and generate embeddings."""
    reviews = context['ti'].xcom_pull(key='reviews', task_ids='fetch_reviews')
    
    if not reviews:
        logger.info("No reviews to process")
        return 0
    
    df = DataPreprocessor.preprocess_cloud_review_records(reviews)
    
    if df.empty:
        logger.warning("No valid reviews after preprocessing")
        return 0
    
    api_key = Variable.get('GOOGLE_API_KEY')
    embedding_generator = EmbeddingGenerator(
        api_key=api_key,
        batch_size=BATCH_SIZE
    )
    
    texts = df['combined_text'].tolist()
    embeddings = embedding_generator.generate_embeddings(texts)
    
    review_embeddings = []
    for i, row in df.iterrows():
        review_embeddings.append({
            'review_id': row['review_id'],
            'embedding': embeddings[i]
        })
    
    context['ti'].xcom_push(key='review_embeddings', value=review_embeddings)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return len(embeddings)


def update_review_embeddings(**context):
    """Update product_reviews table with generated embeddings."""
    review_embeddings = context['ti'].xcom_pull(
        key='review_embeddings', 
        task_ids='generate_embeddings'
    )
    
    if not review_embeddings:
        logger.info("No embeddings to update")
        return 0
    
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        update_query = """
            UPDATE product_reviews
            SET embedding = %s::vector
            WHERE review_id = %s;
        """
        
        for item in review_embeddings:
            embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'
            cursor.execute(update_query, (embedding_str, item['review_id']))
        
        connection.commit()
        logger.info(f"Updated {len(review_embeddings)} review embeddings")
        return len(review_embeddings)
        
    except Exception as e:
        connection.rollback()
        logger.error(f"Error updating embeddings: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()


fetch_task = PythonOperator(
    task_id='fetch_reviews',
    python_callable=fetch_reviews_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_review_embeddings,
    dag=dag,
)

fetch_task >> generate_task >> update_task
