from langchain_openai import OpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.vectorstores import Pinecone
import pinecone
from config import OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT

# Initialize Pinecone
pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)


def create_qa_chain(index):
    """
    Creates a ConversationalRetrievalChain for RAG.
    """
    # Initialize the LLM
    llm = OpenAI(model="gpt-3.5-turbo-instruct", temperature=0.3,openai_api_key=OPENAI_API_KEY)

    # Wrap the Pinecone index as a retriever
    retriever = Pinecone(index).as_retriever()

    # Create the conversational chain
    qa_chain = ConversationalRetrievalChain.from_llm(llm=llm, retriever=retriever)

    return qa_chain

def answer_question(qa_chain, question, chat_history):
    """Answer user questions based on the document."""
    result = qa_chain({"question": question, "chat_history": chat_history})
    return result["answer"]

