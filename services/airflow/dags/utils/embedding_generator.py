"""
Embedding generation utility for Airflow DAGs.
Handles batch processing of text embeddings using Google Gemini API.
"""
import logging
import time
from typing import List
import google.generativeai as genai

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generates embeddings using Google Gemini API with batch processing and rate limiting.
    """
    
    def __init__(self, api_key: str, model: str = "models/embedding-001", batch_size: int = 100):
        """
        Initialize the embedding generator.
        
        Args:
            api_key: Google API key for Gemini
            model: Embedding model name (default: models/embedding-001, 768 dimensions)
            batch_size: Number of texts to process per API call (default: 100)
        """
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for embedding generation")
        
        self.api_key = api_key
        self.model = model
        self.batch_size = batch_size
        
        # Configure Gemini API
        genai.configure(api_key=self.api_key)
        logger.info(f"EmbeddingGenerator initialized with model: {self.model}, batch_size: {self.batch_size}")
    
    def generate_embeddings(self, text_list: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            text_list: List of text strings to embed
            
        Returns:
            List of embedding vectors (768-dimensional floats)
            
        Raises:
            Exception: If embedding generation fails
        """
        if not text_list:
            logger.warning("Empty text list provided for embedding generation")
            return []
        
        embeddings = []
        total = len(text_list)
        logger.info(f"Starting embedding generation for {total} texts")
        
        for i in range(0, total, self.batch_size):
            batch = text_list[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total + self.batch_size - 1) // self.batch_size
            
            try:
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} texts)")
                
                # Generate embeddings via Gemini
                result = genai.embed_content(
                    model=self.model,
                    content=batch,
                    task_type="retrieval_document",
                    title="Embedding of ecommerce data"
                )
                
                embeddings.extend(result['embedding'])
                logger.info(f"Batch {batch_num}/{total_batches} completed. Total processed: {len(embeddings)}/{total}")
                
                # Rate limiting to avoid API throttling
                if i + self.batch_size < total:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {batch_num} (indices {i}-{i+len(batch)}): {e}")
                raise
        
        logger.info(f"Successfully generated {len(embeddings)} embeddings")
        return embeddings
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a single query text.
        
        Args:
            query: Query string to embed
            
        Returns:
            Embedding vector (768-dimensional floats)
        """
        try:
            result = genai.embed_content(
                model=self.model,
                content=query,
                task_type="retrieval_query"  # Different task type for queries
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise
