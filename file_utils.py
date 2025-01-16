from langchain_community.document_loaders import PyPDFLoader
import spacy
import pdfplumber
import re

nlp = spacy.load('en_core_web_sm')

def parse_and_extract(file_path):
    """Parse and extract key information from a PDF."""
    # Load the PDF document
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    # Extract text from the document
    text = " ".join([doc.page_content for doc in documents])

    # Use spaCy for Named Entity Recognition (NER)
    doc = nlp(text)
    extracted_info = {
        "title": text.split("\n")[0],  # First line is typically the title
        "emails": [word for word in text.split() if "@" in word and "." in word],
    }
    return extracted_info, documents

def extract_authors_and_organizations(file_path):
    """Extract authors and organizations using layout-based extraction with PDFPlumber."""
    authors = []
    organizations = []
    with pdfplumber.open(file_path) as pdf:
        # Process the first page only
        first_page = pdf.pages[0]
        text = first_page.extract_text()
        if not text:
            raise ValueError("No text found on the first page of the PDF.")
        
        # Extract lines from the text
        lines = text.split("\n")
        
        # Process lines to extract names and organizations
        for line in lines[1:6]:
            if "Abstract" in line:
                break
            # Fallback: Use regex to extract additional names
            name_pattern = (
                r'\b([A-Z][a-z]+[A-Z][a-z]+)(?:\d+|\*\d+|\d+\+)?\b'  # Matches patterns like "Firstname Lastname12"
            )
            regex_names = re.findall(name_pattern,line)
            authors.extend(regex_names)
            
            # Fallback: Identify organization-like phrases
            org_pattern = r'(?:\d+)?([A-Z][a-zA-Z]*(?:[A-Z][a-zA-Z]*)*)'
            regex_orgs = re.findall(org_pattern,line)
            organizations.extend(regex_orgs)
                  
    
    # Deduplicate results
    authors = list(set(authors))
    authors = [author for author in authors if not any(word.lower() in author.lower() for word in ["university", "institute"])]
    organizations = list(set(organizations)-set(authors))

    return authors, organizations
