# SciChat 

AI Chatbot Tool powered by RAG(Retrieval-Augmented Generation) to chat with Scientific Papers. This application allows users to upload scientific papers, extract key information, and have interactive conversations about the papers' content using RAG .

## Features

- **Paper Upload**: Upload and process scientific PDF papers
- **Information Extraction**: Automatically extract titles, authors, organizations, and contact information
- **Semantic Search**: Search through papers using natural language queries
- **Interactive Chat**: Ask questions about papers and get accurate answers
- **Dashboard**: View statistics and recent activity
- **Paper Management**: Browse and search through your uploaded papers

## Tech Stack

- **Backend**: FastAPI, Python 3.8+
- **Database**: Pinecone (Vector Database)
- **NLP**: LangChain, SentenceTransformers, spaCy
- **PDF Processing**: PyPDF, PDFPlumber
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5

## Project Structure

```
scichat/
├── app.py                 # FastAPI application
├── config.py              # Configuration settings
├── embedding_utils.py     # Vector embedding utilities
├── file_utils.py          # PDF parsing utilities
├── qa_utils.py            # Question answering utilities
├── static/                # Static files (CSS, JS)
│   ├── css/
│   │   └── style.css      # Dashboard styles
│   └── js/
│       └── main.js        # Dashboard JavaScript
├── templates/             # HTML templates
│   └── index.html         # Main dashboard template
├── uploads/               # Uploaded PDF files
└── requirements.txt       # Python dependencies
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/scichat.git
   cd scichat
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Install the spaCy model:
   ```
   python -m spacy download en_core_web_sm
   ```

4. Create a `.env` file in the project root with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_ENVIRONMENT=your_pinecone_environment
   ```

5. Create the necessary directories:
   ```
   mkdir -p static/css static/js templates uploads
   ```

6. Start the application:
   ```
   uvicorn app:app --reload
   ```

7. Open your browser and navigate to `http://localhost:8000`

## Usage

1. **Upload a Paper**: Click on the "Upload" tab and select a scientific PDF paper to upload.

2. **View Papers**: Navigate to the "Papers" tab to see all uploaded papers.

3. **Chat with Papers**: Click on the "Chat" tab to start asking questions about your papers.

4. **Dashboard**: The dashboard shows an overview of your activity, including recent papers and questions.

