from sentence_transformers import SentenceTransformer
import pinecone
import os
from dotenv import load_dotenv
load_dotenv()
pine_api_key = os.getenv("PINE_API_KEY")
pinecone.init(api_key=pine_api_key, environment="us-west1-gcp")

# Initialize the SentenceTransformer model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text):
    """Generate embeddings using SentenceTransformer."""
    return embedding_model.encode(text, convert_to_tensor=False)

def process_and_store_embeddings(documents, section_titles):
    """Process documents and store embeddings in Pinecone."""
    index_name = "document-embeddings"  
    dimension = 384  # Dimension of the 'all-MiniLM-L6-v2' model

    # Create the Pinecone index if it doesn't exist
    if index_name not in pinecone.list_indexes():
        pinecone.create_index(index_name, dimension=dimension)
    index = pinecone.Index(index_name)

    all_embeddings = []
    metadata = []

    for document in documents:
        document_id = document.get("id")  # Document ID

        # Get embeddings for title, authors, organization, email, content, and full document
        title_embedding = get_embedding(document.get("title", ""))
        author_embedding = get_embedding(document.get("authors", ""))
        org_embedding = get_embedding(document.get("organizations", ""))
        email_embedding = get_embedding(document.get("emails", ""))
        content_embedding = get_embedding(document.get("content", ""))
        full_doc_embedding = get_embedding(document.get("full_content", ""))

        # Store embeddings and metadata
        all_embeddings.extend([title_embedding, author_embedding, org_embedding, email_embedding, content_embedding, full_doc_embedding])
        metadata.extend([
            {"type": "title", "document_id": document_id},
            {"type": "authors", "document_id": document_id},
            {"type": "organizations", "document_id": document_id},
            {"type": "emails", "document_id": document_id},
            {"type": "content", "document_id": document_id},
            {"type": "full_document", "document_id": document_id}
        ])

    # Upsert the embeddings into Pinecone
    index.upsert(vectors=[(str(i), embedding.tolist(), metadata[i]) for i, embedding in enumerate(all_embeddings)])

    return index