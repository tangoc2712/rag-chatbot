"""
Cloud Product Embedding DAG
Generates embeddings for products table in cloud PostgreSQL.
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

# Load configuration from Airflow Variables
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
    'cloud_product_embedding_generation',
    default_args=default_args,
    description='Generate embeddings for cloud products table',
    schedule_interval=config['schedules']['product_embedding'],
    catchup=False,
    tags=['cloud', 'embedding', 'products', 'high-priority'],
)


def fetch_products_without_embeddings(**context):
    """Fetch products that don't have embeddings yet."""
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    query = """
        SELECT product_id, name, description, price, category_id, sku,
               product_url, currency, is_active, created_at, updated_at
        FROM products
        WHERE embedding IS NULL
        ORDER BY created_at DESC;
    """
    
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        
        products = [dict(zip(columns, record)) for record in records]
        logger.info(f"Found {len(products)} products without embeddings")
        
        # Push to XCom for next task
        context['ti'].xcom_push(key='products', value=products)
        
        return len(products)
        
    finally:
        cursor.close()
        connection.close()


def process_and_generate_embeddings(**context):
    """Preprocess products and generate embeddings."""
    products = context['ti'].xcom_pull(key='products', task_ids='fetch_products')
    
    if not products:
        logger.info("No products to process")
        return 0
    
    # Preprocess products
    df = DataPreprocessor.preprocess_cloud_product_records(products)
    
    if df.empty:
        logger.warning("No valid products after preprocessing")
        return 0
    
    # Generate embeddings
    api_key = Variable.get('GOOGLE_API_KEY')
    embedding_generator = EmbeddingGenerator(
        api_key=api_key,
        batch_size=BATCH_SIZE
    )
    
    texts = df['combined_text'].tolist()
    embeddings = embedding_generator.generate_embeddings(texts)
    
    # Prepare data for database update
    product_embeddings = []
    for i, row in df.iterrows():
        product_embeddings.append({
            'product_id': row['product_id'],
            'embedding': embeddings[i]
        })
    
    # Push to XCom
    context['ti'].xcom_push(key='product_embeddings', value=product_embeddings)
    
    logger.info(f"Generated {len(embeddings)} embeddings")
    return len(embeddings)


def update_product_embeddings(**context):
    """Update products table with generated embeddings."""
    product_embeddings = context['ti'].xcom_pull(
        key='product_embeddings', 
        task_ids='generate_embeddings'
    )
    
    if not product_embeddings:
        logger.info("No embeddings to update")
        return 0
    
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    connection = postgres_hook.get_conn()
    cursor = connection.cursor()
    
    try:
        update_query = """
            UPDATE products
            SET embedding = %s::vector
            WHERE product_id = %s;
        """
        
        for item in product_embeddings:
            embedding_str = '[' + ','.join(map(str, item['embedding'])) + ']'
            cursor.execute(update_query, (embedding_str, item['product_id']))
        
        connection.commit()
        logger.info(f"Updated {len(product_embeddings)} product embeddings")
        
        return len(product_embeddings)
        
    except Exception as e:
        connection.rollback()
        logger.error(f"Error updating embeddings: {str(e)}")
        raise
    finally:
        cursor.close()
        connection.close()


# Define tasks
fetch_task = PythonOperator(
    task_id='fetch_products',
    python_callable=fetch_products_without_embeddings,
    dag=dag,
)

generate_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=process_and_generate_embeddings,
    dag=dag,
)

update_task = PythonOperator(
    task_id='update_embeddings',
    python_callable=update_product_embeddings,
    dag=dag,
)

# Set task dependencies
fetch_task >> generate_task >> update_task
