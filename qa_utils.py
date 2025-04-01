import os
from langchain_openai import OpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain_pinecone import Pinecone
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
import pinecone
from dotenv import load_dotenv
import logging
from embedding_utils import determine_text_key

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
pine_api_key = os.getenv("PINECONE_API_KEY")
pine_env = os.getenv("PINECONE_ENVIRONMENT")
openai_key = os.getenv("OPENAI_API_KEY")

# Initialize embeddings model
embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Initialize Pinecone
try:
    pine_env = os.getenv("PINECONE_ENVIRONMENT")
    logger.info("Pinecone initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {str(e)}")
    raise

def create_qa_chain(index):
    """
    Creates a ConversationalRetrievalChain for RAG.
    
    Args:
        index: Pinecone index object
        
    Returns:
        ConversationalRetrievalChain object
    """
    try:
        # Define the prompt template for the QA chain
        qa_template = """You are a specialized scientific research assistant with expertise in analyzing academic papers.

        CONTEXT INFORMATION:
        {context}

        Given the above information from a scientific paper, please answer the following question with precision and academic rigor. Don't 
        Hallucinate take information only from the context provided and the Paper to answer the questions precisely.

        USER QUESTION: {question}

        Guidelines for your response:
        1. Focus only on information explicitly stated in the provided question by the user.
        2. Avoid making assumptions or inferences not supported by the provided context.
        3. Maintain scientific terminology used in the original paper
        4. If asked about authors, titles, or affiliations, provide that information precisely and breifly, 
        don't elaborate on it, just give the reuired  answer like author names , organizations etc.
        5. If information is not available in the context, clearly state this limitation rather than speculating
        6. When discussing experimental findings, distinguish between empirical observations and theoretical proposals
        7. Structure complex answers with appropriate organization when needed
        8. Maintain an academic tone throughout
        9. For specific details like numerical results or statistical significance, provide exact values when available.
        10. When asked about authors, titles or affiliations , but you are not able to get answers from provided context information,
        reference the full document or the paper's metadata for the required information.
        
        Answer:"""
        
        QA_PROMPT = PromptTemplate(
            template=qa_template, 
            input_variables=["context", "question"]
        )
        
        # Initialize the LLM (OpenAI model) - FIXED: Using OpenAI instead of ChatOpenAI
        # and using gpt-3.5-turbo-instruct which is a completion model
        llm = OpenAI(
            model="gpt-3.5-turbo-instruct", 
            temperature=0.3,
            openai_api_key=openai_key
        )
        
        # Create a retriever that wraps the Pinecone index
        retriever = Pinecone(
            index=index, 
            embedding=embedding, 
            text_key='text'
        ).as_retriever(
            search_type="similarity",
            search_kwargs={"k": 10}  
        )
        
        # Create the conversational chain
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            return_source_documents=False,
            verbose=True,
            chain_type="stuff",
            combine_docs_chain_kwargs={"prompt": QA_PROMPT}
        )
        
        logger.info("QA chain created successfully")
        return qa_chain
    
    except Exception as e:
        logger.error(f"Error creating QA chain: {str(e)}")
        raise

def answer_question(qa_chain, question, chat_history, metadata_only=False):
    """
    Answer user questions based on the document.
    
    Args:
        qa_chain: The ConversationalRetrievalChain
        question: User's question
        chat_history: Previous conversation history
        metadata_only: If True, only search specific metadata fields
        
    Returns:
        Answer string
    """
    try:
        # Determine if this is a metadata-specific query
        if metadata_only:
            text_key = determine_text_key(question)
            logger.info(f"Metadata search: Using text_key '{text_key}'")
            
            # Update the retriever's search parameters to focus on the specific field
            qa_chain.retriever.search_kwargs["filter"] = {"type": text_key}
        else:
            # For general questions, prioritize content chunks but don't exclude metadata
            if "filter" in qa_chain.retriever.search_kwargs:
                qa_chain.retriever.search_kwargs.pop("filter")
        
        # Get the answer
        result = qa_chain({"question": question, "chat_history": chat_history})
        
        # Enhance the answer with source information
        answer = result["answer"]
        
        logger.info(f"Generated answer for question: {question[:50]}...")
        return answer
    
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        return f"I'm sorry, I encountered an error while processing your question. Error: {str(e)}"