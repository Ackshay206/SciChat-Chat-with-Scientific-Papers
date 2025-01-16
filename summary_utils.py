from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAI
from config import OPENAI_API_KEY


def summarize_sections(documents, section_titles):
    """
    Summarize each section of the paper using LangChain with GPT-3.5 Turbo.
    """
    for document in documents:
        lines = document.page_content.split("\n")
        # Skip the first 5 lines *only if* they contain metadata (title, authors, etc.)
        if "Abstract" not in lines[0:5]:  # Ensure you're not skipping the Abstract
            document.page_content = "\n".join(lines[5:])
        
        
    # Split the document into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=150)
    chunks = text_splitter.split_documents(documents)

    # Initialize a dictionary to store section-wise content
    summaries = {}

    # Initialize LangChain LLM
    llm = OpenAI(model="gpt-3.5-turbo-instruct", temperature=0.3, max_tokens =300, openai_api_key=OPENAI_API_KEY)

    # Create a prompt template
    prompt_template = PromptTemplate(
        input_variables=["section_title", "content"],
        template=(
            "You are a helpful assistant summarizing sections of a research paper. "
            "Please summarize the content under the section titled '{section_title}' based on the following content:\n\n"
            "{content}\n\n"
            "Provide a detailed, in-depth summary of the section in 250 words, including key points, "
            "arguments, and supporting details."
        )
    )

    summarization_chain = LLMChain(llm=llm, prompt=prompt_template)

    for section_title, fallbacks in section_titles.items():
        # Extract all chunks for the primary or fallback titles
        section_text = None
        for title_option in [section_title] + fallbacks:
            section_text = " ".join([
                chunk.page_content for chunk in chunks
                if title_option.lower() in chunk.page_content.lower()
            ])
            if section_text.strip():  # If content is found, stop looking at fallbacks
                break
        

        # Summarize content for other sections
        if section_text and section_text.strip():
            summaries[section_title] = summarization_chain.run({
                "section_title": section_title,
                "content": section_text
            })

        # Handle missing content
        else:
            summaries[section_title] = f"No content found for {section_title}."

    return summaries