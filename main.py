import os
import sys
import argparse
import logging
from typing import Dict, Any
from file_utils import parse_and_extract, extract_authors_and_organizations
from embedding_utils import process_and_store_embeddings
from qa_utils import create_qa_chain, answer_question
from dotenv import load_dotenv
import pinecone
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

pine_api_key = os.getenv("PINECONE_API_KEY")
pine_env = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")

def process_pdf(file_path: str) -> Dict[str, Any]:
    """
    Process a PDF file and return structured data for embedding.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Dictionary containing structured data extracted from the PDF
    """
    logger.info(f"Processing PDF: {file_path}")
    
    try:
        # Extract basic information and full content using parse_and_extract
        # This will return extracted_info and documents
        extracted_info, documents = parse_and_extract(file_path)
        
        # Extract authors and organizations using extract_authors_and_organizations
        authors, organizations = extract_authors_and_organizations(file_path)
        
        # If we still don't have authors, try to extract from the first page
        if not authors and documents and len(documents) > 0:
            logger.info("Trying to extract authors from first page content")
            first_page = documents[0].page_content
            
            # Look for lines with multiple capitalized words, common in author lists
            lines = first_page.split('\n')
            for line in lines[:10]:  # Check first 10 lines
                # Skip very short lines, abstract, title-like lines
                if len(line) < 10 or "abstract" in line.lower() or line.isupper():
                    continue
                
                # Look for lines with multiple capitalized words (potential author names)
                words = line.split()
                cap_words = [w for w in words if w and w[0].isupper()]
                
                # If line has several capitalized words and not too many words total, might be author list
                if len(cap_words) >= 2 and len(words) < 15 and not any(w.endswith('.') for w in words[-2:]):
                    # Extract potential names (First Last pairs)
                    for i in range(len(words) - 1):
                        if words[i] and words[i+1] and words[i][0].isupper() and words[i+1][0].isupper():
                            potential_author = f"{words[i]} {words[i+1]}"
                            # Filter out organization-like names
                            if not any(org_word in potential_author.lower() for org_word in 
                                      ["university", "institute", "department", "abstract"]):
                                authors.append(potential_author)
        
        # Clean up authors (remove any with numbers or special characters)
        authors = [author for author in authors if re.match(r'^[A-Za-z\s\.\-]+$', author)]
        
        # Get the filename for ID
        file_id = os.path.basename(file_path)
        
        # Combined extracted information
        document_data = {
            "id": file_id,
            "title": extracted_info["title"] or "Unknown Title",
            "authors": ", ".join(authors) or "Unknown Authors",
            "organizations": ", ".join(organizations) or "Unknown Organizations",
            "emails": ", ".join(extracted_info["emails"]) or "No email information",
            "content": extracted_info.get("abstract", "") or "No abstract available", 
            "full_content": extracted_info["content"] or "No content available",
        }
        
        # Log extraction results
        logger.info(f"Extracted document ID: {document_data['id']}")
        logger.info(f"Extracted title: {document_data['title']}")
        logger.info(f"Extracted authors: {document_data['authors']}")
        logger.info(f"Extracted organizations: {document_data['organizations']}")
        logger.info(f"Extracted emails: {document_data['emails']}")
        
        return document_data
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise

def main():
    """Main function to run the SciChat application"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="SciChat - Chat with scientific papers")
    parser.add_argument("--pdf", type=str, help="Path to the PDF file to process")
    parser.add_argument("--process_only", action="store_true", help="Only process the PDF without starting the chat")
    args = parser.parse_args()
    
    # If no arguments are provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # Check environment variables
    if not pine_api_key:
        logger.error("Pinecone API key not found. Please set PINE_API_KEY in your .env file.")
        return
    
    # Initialize Pinecone
    try:
        logger.info("Connecting to Pinecone...")
        pc = pinecone.init(api_key=pine_api_key, environment=pine_env)
    except Exception as e:
        logger.error(f"Failed to initialize Pinecone: {str(e)}")
        return
    
    # Connect to the existing index
    index_name = "document-embeddings"
    try:
        if index_name in pc.list_indexes().names():
            logger.info(f"Connecting to existing Pinecone index: {index_name}")
            index = pc.Index(index_name)
        else:
            logger.info(f"Index {index_name} does not exist yet.")
            index = None
    except Exception as e:
        logger.error(f"Error connecting to Pinecone index: {str(e)}")
        return
    
    # Process PDF if provided
    if args.pdf:
        try:
            if not os.path.exists(args.pdf):
                logger.error(f"PDF file not found: {args.pdf}")
                return
                
            logger.info(f"Processing PDF file: {args.pdf}")
            document_data = process_pdf(args.pdf)
            
            # Generate and store embeddings
            logger.info("Generating embeddings and storing in Pinecone...")
            index = process_and_store_embeddings([document_data])
            
            if index:
                logger.info("Document processing completed successfully!")
            else:
                logger.error("Failed to process document. Check logs for details.")
                return
            
            # Exit if only processing was requested
            if args.process_only:
                return
                
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            if args.process_only:
                return
    
    # Check if we have a valid index before proceeding to chat
    if not index:
        logger.error("No valid Pinecone index found. Please process a PDF first.")
        return
    
    # Create QA chain for the chatbot
    try:
        logger.info("Creating QA chain for the chatbot...")
        qa_chain = create_qa_chain(index)
    except Exception as e:
        logger.error(f"Error creating QA chain: {str(e)}")
        return
    
    # Start the chatbot interface
    logger.info("Chatbot is ready! Type 'exit' to quit.")
    print("=" * 50)
    print("Welcome to SciChat! You can ask questions about the scientific papers.")
    print("Type 'exit' to quit, 'help' for assistance.")
    print("=" * 50)

    chat_history = []

    while True:
        # Get user input
        question = input("\nYou: ").strip()
        
        # Exit command
        if question.lower() in ["exit", "quit", "bye"]:
            print("Goodbye!")
            break
            
        # Help command
        if question.lower() in ["help", "?"]:
            print("\nSciChat Help:")
            print("- Ask questions about the paper content")
            print("- Ask about specific authors, organizations, or emails")
            print("- For metadata, try queries like 'who wrote this paper?' or 'what university is this from?'")
            print("- Type 'exit' to quit the chatbot")
            continue
            
        # Skip empty questions
        if not question:
            continue
            
        # Determine if this is a metadata-specific question
        metadata_question = any(word in question.lower() for word in 
                               ["author", "who wrote", "organization", "university", 
                                "email", "contact", "title", "called"])
        
        try:
            # Get the answer
            print("\nThinking...")
            answer = answer_question(qa_chain, question, chat_history, metadata_only=metadata_question)
            
            # Display the answer
            print(f"\nBot: {answer}")
            
            # Update chat history
            chat_history.append((question, answer))
            
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            print(f"\nBot: I'm sorry, I encountered an error while processing your question. Please try again.")

if __name__ == "__main__":
    main()