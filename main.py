import os
from file_utils import parse_and_extract, extract_authors_and_organizations
from embedding_utils import process_and_store_embeddings
from qa_utils import create_qa_chain, answer_question
from dotenv import load_dotenv
import pinecone

# Load environment variables
load_dotenv()

pine_api_key = os.getenv("PINE_API_KEY")
pine_env = os.getenv("PINECONE_ENVIRONMENT")

pc = pinecone.Pinecone(api_key=pine_api_key, environment=pine_env)

def process_pdf(file_path):
    """
    Process a PDF file and return structured data for embedding.
    """
    # Extract basic information and full content
    extracted_info, documents = parse_and_extract(file_path)
    
    # Extract authors and organizations
    authors, organizations = extract_authors_and_organizations(file_path)

    # Combine all extracted information into a single dictionary
    document_data = {
        "id": os.path.basename(file_path), 
        "title": extracted_info["title"],
        "authors": ", ".join(authors),  
        "organizations": ", ".join(organizations),
        "emails": ", ".join(extracted_info["emails"]), 
        "content": extracted_info["content"], 
        "full_content": extracted_info["content"], 
    }
    
    print(document_data["id"])
    print(document_data["title"])
    print(document_data["authors"])
    print(document_data["organizations"])
    print(document_data["emails"])
    return document_data

def main():
    # Path to the PDF file you want to process
    pdf_file_path = r"C:\Users\acksh\OneDrive\Desktop\GAI\SciChat\Liu_Video_Swin_Transformer_CVPR_2022_paper.pdf"

    # Step 1: Process the PDF and extract structured data
    print("Extracting information from the PDF...")
    document_data = process_pdf(pdf_file_path)

    index_name = "document-embeddings"  
    print(f"Connecting to the existing Pinecone index: {index_name}")

    index =pc.Index(index_name)

    # Step 2: Generate embeddings and store them in Pinecone
    print("Generating embeddings and storing in Pinecone...")
    process_and_store_embeddings([document_data])

    print("Process completed successfully!")

    # Step 2: Create a QA chain for the chatbot
    print("Creating QA chain for the chatbot...")
    qa_chain = create_qa_chain(index)

    # Step 3: Start the chatbot
    print("Chatbot is ready! Type 'exit' to quit.")

    chat_history = []  

    while True:
        # Get user input
        question = input("You: ")
        
        # Exit the chatbot if the user types 'exit'
        if question.lower() == "exit":
            print("Goodbye!")
            break

        # Get the answer from the QA chain
        answer = answer_question(qa_chain, question, chat_history)

        # Display the answer
        print(f"Bot: {answer}")

        # Update chat history
        chat_history.append((question, answer))

if __name__ == "__main__":
    main()