from sentence_transformers import SentenceTransformer
import pinecone
import os
from dotenv import load_dotenv
load_dotenv()
pine_api_key = os.getenv("PINE_API_KEY")
pc = pinecone.Pinecone(api_key=pine_api_key)

# Initialize the SentenceTransformer model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


def determine_text_key(query):
    """Determine which text_key to use based on the query."""
    query = query.lower()
    if "title" in query:
        return "title"
    elif "author" in query:
        return "authors"
    elif "organization" in query:
        return "organizations"
    elif "email" in query:
        return "emails"
    elif "summary" in query:
        return "content"
    else:
        return "full_content"
    
def get_embedding(text):
    """Generate embeddings using SentenceTransformer."""
    return embedding_model.encode(text, convert_to_tensor=False)

def process_and_store_embeddings(documents):
    """Process documents and store embeddings in Pinecone."""
    index_name = "document-embeddings"  
    dimension = 384  # Dimension of the 'all-MiniLM-L6-v2' model

    if index_name not in pc.list_indexes().names():
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
        all_embeddings.extend([title_embedding, author_embedding, org_embedding, email_embedding,content_embedding, full_doc_embedding])
        metadata.extend([
            {"type": "title", "document_id": document_id, "text": document.get("title", "")},
            {"type": "authors", "document_id": document_id, "text": document.get("authors", "")},
            {"type": "organizations", "document_id": document_id, "text": document.get("organizations", "")},
            {"type": "emails", "document_id": document_id, "text": document.get("emails", "")},
            {"type": "content", "document_id": document_id, "text": document.get("content", "")},
            {"type": "full_document", "document_id": document_id, "text": document.get("full_content", "")}
        ])

    # Upsert the embeddings into Pinecone
    index.upsert(vectors=[(f"{document_id}_{i}", embedding.tolist(), metadata[i]) for i, embedding in enumerate(all_embeddings)])

    return index