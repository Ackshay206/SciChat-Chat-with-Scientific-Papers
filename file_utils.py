from langchain_community.document_loaders import PyPDFLoader
import spacy
import pdfplumber
import re
import os
import argparse
import json
from typing import Tuple, Dict, List, Any

# Load spaCy NER model
nlp = spacy.load('en_core_web_sm')

def parse_and_extract(file_path: str) -> Tuple[Dict[str, Any], List]:
    """
    Parse and extract key information from a PDF.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Tuple containing extracted info dictionary and document chunks
    """
    # Validate file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    # Load the PDF document
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    
    # Extract text from the document
    text = " ".join([doc.page_content for doc in documents])
    
    # Extract title more intelligently - usually first few lines of first page
    title = ""
    if documents and len(documents) > 0:
        first_page_lines = documents[0].page_content.split('\n')
        # Usually title is in the first 5 lines and doesn't have common metadata markers
        for line in first_page_lines[:5]:
            line = line.strip()
            if line and len(line) > 10 and not any(x in line.lower() for x in ['abstract', 'introduction', 'university', '@']):
                title = line
                break
    
    if not title and len(first_page_lines) > 0:
        title = first_page_lines[0]  # Fallback to first line
    
    # Extract emails using more robust regex
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    
    # Also look for email patterns in braces or brackets
    brace_email_pattern = r'\{([A-Za-z0-9._%+-]+(?:,[A-Za-z0-9._%+-]+)*)\}@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
    brace_matches = re.findall(brace_email_pattern, text, re.IGNORECASE)
    for usernames, domain in brace_matches:
        for username in usernames.split(','):
            emails.append(f"{username.strip()}@{domain}")
    
    # Use spaCy for content extraction and summary
    doc = nlp(text[:50000])  # Limit to first 50K chars for processing speed
    
    # Create an initial summary from the abstract
    abstract = ""
    abstract_pattern = r'Abstract\s*\n(.*?)(?:\n\n|\n[A-Z][a-z]*\s*\n|$)'
    abstract_matches = re.search(abstract_pattern, text, re.DOTALL)
    if abstract_matches:
        abstract = abstract_matches.group(1).strip()
    
    # Combine all extracted information
    extracted_info = {
        "title": title,
        "emails": emails,
        "content": text,
        "abstract": abstract
    }
    
    return extracted_info, documents

def extract_authors_and_organizations(file_path: str) -> Tuple[List[str], List[str]]:
    """
    Extract authors and organizations using layout-based extraction with PDFPlumber.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Tuple of (authors list, organizations list)
    """
    authors = []
    organizations = []
    
    try:
        # First attempt: Use pdfplumber to extract text and analyze
        with pdfplumber.open(file_path) as pdf:
            # Process the first page only - that's where author info usually is
            if len(pdf.pages) > 0:
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                if not text:
                    print(f"Warning: pdfplumber could not extract text from first page")
                    return [], []
                
                # Debug: Print first page content
                print(f"DEBUG - First page content: {text[:200]}...")
                
                # Extract lines from the text
                lines = text.split("\n")
                
                # Look for author section - typically between title and abstract
                found_title = False
                abstract_found = False
                
                for i, line in enumerate(lines[:15]):  # Check first 15 lines
                    # Skip empty lines
                    if not line.strip():
                        continue
                    
                    # Debug each line
                    print(f"DEBUG - Line {i}: {line}")
                    
                    # Skip until we find the title
                    if not found_title:
                        if i >= 1 and len(line.strip()) > 10:
                            found_title = True
                            continue  # Skip the title line
                    
                    # Stop when we reach abstract
                    if "Abstract" in line:
                        abstract_found = True
                        break
                    
                    # Area between title and abstract often contains authors
                    if found_title and not abstract_found:
                        # Common author patterns in academic papers
                        # Include patterns for joined names with superscripts
                        name_patterns = [
                            # Standard format with space
                            r'([A-Z][a-z]+\s+[A-Z][a-z]+)[ \t]*(?:[\d\*\†\‡\§\|\#\+]{1,2}|\[\d+\]|\{[^\}]+\}|(?:https?|mailto):[^\s]+)?\b',
                            
                            # Joined names with superscripts (CamelCase)
                            r'([A-Z][a-z]+[A-Z][a-z]+)[\*\d\†\‡\§\|\#\+]{1,3}\b',
                            
                            # Name with middle initial
                            r'\b([A-Z][a-z]+\s+[A-Z]\.?\s+[A-Z][a-z]+)\b',
                            
                            # Hyphenated names
                            r'\b([A-Z][a-z]+-[A-Z][a-z]+\s+[A-Z][a-z]+)\b',
                            
                            # Names with particles
                            r'\b([A-Z][a-z]+\s+(?:van|von|de|da|del)\s+[A-Z][a-z]+)\b',
                            
                            # Abbreviated first name
                            r'\b([A-Z][a-z]*\.?\s+[A-Z][a-z]+)\b',
                            
                            # Names with 'and' prefix
                            r'\band([A-Z][a-z]+[A-Z][a-z]+)\b',
                            
                            # CamelCase names without superscripts
                            r'([A-Z][a-z]+[A-Z][a-z]+)\b'
                        ]
                        
                        for pattern in name_patterns:
                            found_names = re.findall(pattern, line)
                            if found_names:
                                print(f"DEBUG - Found names: {found_names} with pattern {pattern}")
                                # Clean up names
                                for name in found_names:
                                    # Handle 'and' prefix
                                    if name.startswith('and'):
                                        name = name[3:]  # Remove 'and'
                                    
                                    # Add spaces between camel case names
                                    if ' ' not in name and len(name) > 3:
                                        # Find capital letters after the first one
                                        capitals = [i for i in range(1, len(name)) if name[i].isupper()]
                                        if capitals:
                                            # Insert space before the second capital letter
                                            name = name[:capitals[0]] + ' ' + name[capitals[0]:]
                                    
                                    authors.append(name)
                        
                        # If we have at least one author, check for organizations
                        if authors and i < 10:  # Only check in lines close to authors
                            # Organization patterns - updated to handle joined text
                            org_patterns = [
                                # Standard university/institute pattern with numbering
                                r'(?:\d+)?([A-Z][a-zA-Z]*\s+(?:University|Institute|College|Laboratory|Lab|School|Department|Dept|Center)(?:\s+of\s+[A-Za-z]+)?)',
                                
                                # CamelCase University pattern with numbering
                                r'(?:\d+)?([A-Z][a-zA-Z]*(?:University|Institute|College)(?:of)?[A-Z][a-zA-Z]*(?:and)?[A-Z][a-zA-Z]*)',
                                
                                # Tech company research labs pattern
                                r'(?:\d+)?((?:Microsoft|Google|Apple|Amazon|Facebook|IBM|Intel)\s*(?:Research|Labs|AI|Corporation))',
                                
                                # General "of" pattern
                                r'(?:\d+)?([A-Z][a-zA-Z]*\s+of\s+[A-Z][a-zA-Z]+)',
                                
                                # Simplified institute pattern
                                r'(?:\d+)?([A-Za-z]+\s+(?:Institute|University))',
                            ]
                            for pattern in org_patterns:
                                found_orgs = re.findall(pattern, line)
                                organizations.extend([org.strip() for org in found_orgs if org.strip()])

                # Second pass for superscript-based affiliation extraction
                if not authors:
                    # Try to find authors based on superscripts or common markers
                    superscript_patterns = [
                        r'([A-Z][a-z]+\s+[A-Z][a-z]+)[\d\*\†\‡\§\|\#]+',
                        r'([A-Z][a-z]+[A-Z][a-z]+)[\d\*\†\‡\§\|\#\+]{1,3}',  # CamelCase with superscript
                    ]
                    for pattern in superscript_patterns:
                        for line in lines[:10]:  # Check first 10 lines
                            names = re.findall(pattern, line)
                            if names:
                                print(f"DEBUG - Found names with superscripts: {names}")
                                # Add spaces to CamelCase names
                                for name in names:
                                    if ' ' not in name and len(name) > 3:
                                        capitals = [i for i in range(1, len(name)) if name[i].isupper()]
                                        if capitals:
                                            name = name[:capitals[0]] + ' ' + name[capitals[0]:]
                                    authors.append(name)
    
    except Exception as e:
        print(f"Error extracting authors/organizations: {str(e)}")
        return [], []
    
    # Deduplicate and clean results
    authors = list(set(authors))
    
    # Filter out false positives from author extraction
    authors = [author for author in authors if len(author.split()) >= 2 and 
               not any(word.lower() in author.lower() for word in ["university", "institute", "abstract"])]
    
    # Format CamelCase names that might have been missed
    formatted_authors = []
    for author in authors:
        if ' ' not in author and len(author) > 3:
            # Find all capital letters after the first position
            capitals = [i for i in range(1, len(author)) if author[i].isupper()]
            if capitals:
                # Insert space before the first capital letter after position 0
                formatted_name = author[:capitals[0]] + ' ' + author[capitals[0]:]
                formatted_authors.append(formatted_name)
            else:
                formatted_authors.append(author)
        else:
            formatted_authors.append(author)
    
    # Clean and deduplicate organizations
    organizations = list(set(organizations))
    
    # Format CamelCase organizations
    formatted_orgs = []
    for org in organizations:
        # Try to break CamelCase organization names
        if len(org) > 10 and ' ' not in org:
            # Look for common organization keywords
            for keyword in ['University', 'Institute', 'College', 'Research', 'Technology', 'Science']:
                if keyword in org:
                    index = org.index(keyword)
                    # Add space before keyword if not at the beginning
                    if index > 0:
                        org = org[:index] + ' ' + org[index:]
                    break
        formatted_orgs.append(org)
    
    # Remove organizations that are subsets of other organizations
    filtered_orgs = []
    for org1 in formatted_orgs:
        if not any(org1 != org2 and org1 in org2 for org2 in formatted_orgs):
            filtered_orgs.append(org1)
    
    print(f"DEBUG - Final authors: {formatted_authors}")
    print(f"DEBUG - Final organizations: {filtered_orgs}")
    
    return formatted_authors, filtered_orgs


