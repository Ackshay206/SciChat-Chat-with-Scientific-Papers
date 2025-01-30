import os
from langchain_openai import OpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain_pinecone import Pinecone
import pinecone
from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings

embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

load_dotenv()

pine_api_key = os.getenv("PINE_API_KEY")
pine_env = os.getenv("PINECONE_ENVIRONMENT")
openai_key = os.getenv("OPENAI_API_KEY")

# Initialize Pinecone
pc = pinecone.Pinecone(api_key = pine_api_key, environment = pine_env)

def create_qa_chain(index):
    """
    Creates a ConversationalRetrievalChain for RAG.
    """
    # Initialize the LLM
    llm = OpenAI(model="gpt-3.5-turbo-instruct", temperature=0.3,openai_api_key=openai_key)

    # Wrap the Pinecone index as a retriever
    retriever = Pinecone(index, embedding= embedding, text_key = 'text').as_retriever()

    # Create the conversational chain
    qa_chain = ConversationalRetrievalChain.from_llm(llm=llm, retriever=retriever)

    return qa_chain

def answer_question(qa_chain, question, chat_history):
    """Answer user questions based on the document."""
    result = qa_chain({"question": question, "chat_history": chat_history})
    return result["answer"]

