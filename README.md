# SciChat

SciChat is a tool that enables you to chat with scientific papers. It extracts key information from PDF documents, stores it in a vector database, and allows you to ask questions about the content using natural language.

## Features

- Extract title, authors, organizations, emails, and content from PDF papers
- Generate embeddings and store them in Pinecone for semantic search
- Interactive chat interface to ask questions about the papers
- Support for metadata-specific queries (authors, organizations, etc.)
- Context-aware conversational memory

## Prerequisites

- Python 3.8 or higher
- Pinecone account (free tier available)
- OpenAI API key 
- Spacy English model

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/scichat.git
   cd scichat
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install the spaCy English model:
   ```
   python -m spacy download en_core_web_sm
   ```

4. Create a `.env` file in the project root with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_ENVIRONMENT=your_pinecone_environment  # e.g., gcp-starter
   ```

## Usage

### Processing a PDF

To process a PDF and store its embeddings in Pinecone:

```
python main.py --pdf path/to/your/paper.pdf
```

This will:
1. Extract information from the PDF
2. Generate embeddings
3. Store them in Pinecone
4. Start an interactive chat session

### Process Only (No Chat)

If you want to process a PDF without starting a chat session:

```
python main.py --pdf path/to/your/paper.pdf --process_only
```

### Chat with Processed Papers

After processing one or more papers, you can chat with them:

```
python main.py
```

## Chat Commands

- Type your question about the paper(s) to get an answer
- Type `help` to see available commands
- Type `exit` to quit the chatbot

## Example Questions

- "What is the main finding of this paper?"
- "Who are the authors of this paper?"
- "What university is this paper from?"
- "Explain the methodology used in this study."
- "What were the limitations mentioned in the paper?"

## Customization

You can modify the following parameters in the code:

- `qa_utils.py`: Adjust the prompt template or LLM parameters
- `embedding_utils.py`: Change the embedding model or chunk size
- `main.py`: Update the chatbot interface or processing flow

## Troubleshooting

- **"PDF file not found"**: Ensure the PDF path is correct
- **"API key not found"**: Check your `.env` file has the correct keys
- **"Failed to initialize Pinecone"**: Verify your Pinecone API key and environment
- **"No valid Pinecone index found"**: Process a PDF first before starting the chat

## License

[Your License Here]

## Acknowledgments

This project uses several open-source libraries:
- LangChain
- Pinecone
- Sentence Transformers
- OpenAI API
- spaCy
- PDFPlumber