from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
import os
import tempfile
import uuid
import pinecone
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel
import shutil
from dotenv import load_dotenv

# Import project modules
from file_utils import parse_and_extract, extract_authors_and_organizations
from embedding_utils import process_and_store_embeddings
from qa_utils import create_qa_chain, answer_question

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
pine_api_key = os.getenv("PINECONE_API_KEY")
pine_env = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")

# Create FastAPI instance
app = FastAPI(title="SciChat Dashboard", description="A web interface for the SciChat paper analysis system")

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directory
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Create templates directory for serving the frontend
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Pinecone client
try:
    pc = pinecone.Pinecone(api_key=pine_api_key, environment=pine_env)
    logger.info("Connected to Pinecone")
except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {str(e)}")
    pc = None

# Get or create index
def get_index():
    index_name = "document-embeddings"
    try:
        if pc and index_name in pc.list_indexes().names():
            return pc.Index(index_name)
        return None
    except Exception as e:
        logger.error(f"Error connecting to Pinecone index: {str(e)}")
        return None

# Pydantic models for API
class DocumentMetadata(BaseModel):
    id: str
    title: str
    authors: str
    organizations: str
    emails: str

class QuestionRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None
    metadata_only: Optional[bool] = False

class QuestionResponse(BaseModel):
    answer: str
    conversation_id: str

# Store conversation history
conversation_history = {}

# API routes
@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload", response_model=DocumentMetadata)
async def upload_paper(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload and process a scientific paper"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Save the uploaded file
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract document info
        extracted_info, documents = parse_and_extract(file_path)
        authors, organizations = extract_authors_and_organizations(file_path)
        
        # Create document data
        document_data = {
            "id": file_id,
            "title": extracted_info["title"] or "Unknown Title",
            "authors": ", ".join(authors) or "Unknown Authors",
            "organizations": ", ".join(organizations) or "Unknown Organizations",
            "emails": ", ".join(extracted_info["emails"]) or "No email information",
            "content": extracted_info.get("abstract", "") or "No abstract available", 
            "full_content": extracted_info["content"] or "No content available",
        }
        
        # Process embeddings in the background
        background_tasks.add_task(
            process_and_store_embeddings,
            [document_data]
        )
        
        # Return document metadata
        return DocumentMetadata(
            id=file_id,
            title=document_data["title"],
            authors=document_data["authors"],
            organizations=document_data["organizations"],
            emails=document_data["emails"]
        )
        
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question about the uploaded papers"""
    try:
        # Get conversation history or create new one
        conversation_id = request.conversation_id or str(uuid.uuid4())
        if conversation_id not in conversation_history:
            conversation_history[conversation_id] = []
        
        # Get Pinecone index
        index = get_index()
        if not index:
            raise HTTPException(status_code=503, detail="Search index not available")
        
        # Create QA chain
        qa_chain = create_qa_chain(index)
        
        # Get answer
        chat_history = conversation_history[conversation_id]
        answer = answer_question(
            qa_chain, 
            request.question, 
            chat_history, 
            metadata_only=request.metadata_only
        )
        
        # Update conversation history
        conversation_history[conversation_id].append((request.question, answer))
        
        # Return response
        return QuestionResponse(
            answer=answer,
            conversation_id=conversation_id
        )
        
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/documents", response_model=List[DocumentMetadata])
async def list_documents():
    """List all processed documents"""
    try:
        index = get_index()
        if not index:
            return []
            
        # Query unique document IDs from index
        # This is a simplification - you'll need to implement this based on your vector DB structure
        response = index.query(
            vector=[0] * 384,  # Dummy vector
            top_k=100,
            include_metadata=True
        )
        
        # Extract unique document IDs and metadata
        documents = {}
        for match in response.matches:
            doc_id = match.metadata.get("document_id")
            if doc_id and doc_id not in documents:
                # Try to get title/author matches for this document
                title_match = next((m for m in response.matches if 
                                  m.metadata.get("document_id") == doc_id and 
                                  m.metadata.get("type") == "title"), None)
                                  
                author_match = next((m for m in response.matches if 
                                   m.metadata.get("document_id") == doc_id and 
                                   m.metadata.get("type") == "authors"), None)
                                   
                org_match = next((m for m in response.matches if 
                                m.metadata.get("document_id") == doc_id and 
                                m.metadata.get("type") == "organizations"), None)
                                
                email_match = next((m for m in response.matches if 
                                  m.metadata.get("document_id") == doc_id and 
                                  m.metadata.get("type") == "emails"), None)
                
                documents[doc_id] = DocumentMetadata(
                    id=doc_id,
                    title=title_match.metadata.get("text", "Unknown Title") if title_match else "Unknown Title",
                    authors=author_match.metadata.get("text", "Unknown Authors") if author_match else "Unknown Authors",
                    organizations=org_match.metadata.get("text", "Unknown Organizations") if org_match else "Unknown Organizations",
                    emails=email_match.metadata.get("text", "No email information") if email_match else "No email information"
                )
        
        return list(documents.values())
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        return []

@app.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear a conversation history"""
    if conversation_id in conversation_history:
        conversation_history.pop(conversation_id)
    return {"status": "success"}

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
