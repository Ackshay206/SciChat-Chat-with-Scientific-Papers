from sentence_transformers import SentenceTransformer
import pinecone
import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import logging
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
pine_api_key = os.getenv("PINECONE_API_KEY")

# Initialize Pinecone
try:
    pc = pinecone.Pinecone(api_key=pine_api_key)
    logger.info("Pinecone initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {str(e)}")
    raise

# Initialize the SentenceTransformer model
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("Embedding model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load embedding model: {str(e)}")
    raise

def determine_text_key(query: str) -> str:
    """
    Determine which text_key to use based on the query content.
    
    Args:
        query: The user's search query
        
    Returns:
        The appropriate text_key for vector search
    """
    query = query.lower()
    if any(word in query for word in ["title", "called", "named"]):
        return "title"
    elif any(word in query for word in ["author", "who wrote", "researcher", "scientist"]):
        return "authors"
    elif any(word in query for word in ["organization", "university", "institute", "lab", "where", "affiliation"]):
        return "organizations"
    elif any(word in query for word in ["email", "contact", "reach out"]):
        return "emails"
    else:
        return "chunk"  # Default to content chunks
    
def get_embedding(text: str) -> List[float]:
    """
    Generate embeddings using SentenceTransformer.
    
    Args:
        text: Text to generate embeddings for
        
    Returns:
        Embedding vector as list of floats
    """
    if not text or text.strip() == "":
        logger.warning("Attempted to create embedding for empty text")
        # Return zero vector with correct dimensions
        return [0.0] * 384
    
    try:
        # Get embedding as numpy array and convert to list
        embedding = embedding_model.encode(text, convert_to_tensor=False)
        if isinstance(embedding, np.ndarray):
            return embedding.tolist()
        return embedding  # It's already a list
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        # Return zero vector with correct dimensions
        return [0.0] * 384

def process_and_store_embeddings(documents: List[Dict[str, Any]]) -> Optional[pinecone.Index]:
    """
    Process documents and store embeddings in Pinecone.
    
    Args:
        documents: List of document dictionaries containing extracted metadata
        
    Returns:
        Pinecone index object
    """
    index_name = "document-embeddings"
    dimension = 384  # Dimension of the 'all-MiniLM-L6-v2' model

    try:
        # Check if index exists, create if it doesn't
        if index_name not in pc.list_indexes().names():
            logger.info(f"Creating new Pinecone index: {index_name}")
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=pinecone.ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
        
        # Connect to the index
        index = pc.Index(index_name)
        logger.info(f"Connected to Pinecone index: {index_name}")
        
        all_vectors = []  # Store all vectors to be upserted

        for document in documents:
            document_id = document.get("id", "")
            
            if not document_id:
                logger.warning("Document missing ID field, skipping")
                continue
            
            logger.info(f"Processing document: {document_id}")
            
            # Get metadata fields
            title_text = document.get("title", "")
            authors_text = document.get("authors", "")
            orgs_text = document.get("organizations", "")
            emails_text = document.get("emails", "")
            content_text = document.get("content", "")  # This is typically the abstract
            full_content = document.get("full_content", "")
            
            # Get embeddings for metadata fields
            title_embedding = get_embedding(title_text)
            author_embedding = get_embedding(authors_text)
            org_embedding = get_embedding(orgs_text)
            email_embedding = get_embedding(emails_text)
            
            # Add metadata vectors
            all_vectors.extend([
                (f"{document_id}_title", title_embedding, 
                {"type": "title", "document_id": document_id, "text": title_text}),
                
                (f"{document_id}_authors", author_embedding, 
                {"type": "authors", "document_id": document_id, "text": authors_text}),
                
                (f"{document_id}_organizations", org_embedding, 
                {"type": "organizations", "document_id": document_id, "text": orgs_text}),
                
                (f"{document_id}_emails", email_embedding, 
                {"type": "emails", "document_id": document_id, "text": emails_text}),
            ])
            
            # Process full document content through chunking
            if not full_content or full_content.strip() == "":
                logger.warning(f"Document {document_id} has empty content, skipping chunking")
                continue
                
            # Split the content into chunks - simple method for now
            chunks = []
            chunk_size = 1000
            overlap = 200
            
            for i in range(0, len(full_content), chunk_size - overlap):
                chunk = full_content[i:i + chunk_size]
                if len(chunk.strip()) > 0:  # Skip empty chunks
                    chunks.append(chunk)
            
            logger.info(f"Document split into {len(chunks)} chunks")
            
            # Generate embeddings for each chunk
            for i, chunk in enumerate(chunks):
                chunk_embedding = get_embedding(chunk)
                all_vectors.append(
                    (f"{document_id}_chunk_{i}", chunk_embedding, 
                    {"type": "chunk", "document_id": document_id, "chunk_id": i, "text": chunk})
                )
        
        # Batch upsert to Pinecone
        if all_vectors:
            from tqdm.auto import tqdm
            batch_size = 100
            total_vectors = len(all_vectors)
            
            for i in tqdm(range(0, total_vectors, batch_size), desc="Batches"):
                batch = all_vectors[i:min(i+batch_size, total_vectors)]
                index.upsert(vectors=batch)
            
            logger.info(f"Successfully stored {total_vectors} vectors in Pinecone")
            return index
        else:
            logger.warning("No vectors created for upsert")
            return index
    
    except Exception as e:
        logger.error(f"Error in processing and storing embeddings: {str(e)}")
        return None