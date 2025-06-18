from medAI.config import load_documents, split_documents, get_embeddings, create_or_load_vectorstore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Create or update the vector store index"""
    try:
        logger.info("Loading documents...")
        raw_docs = load_documents("data/")
        logger.info(f"Loaded {len(raw_docs)} documents")
        
        logger.info("Splitting documents...")
        chunks = split_documents(raw_docs)
        logger.info(f"Created {len(chunks)} chunks")
        
        logger.info("Getting embeddings...")
        embeddings = get_embeddings()
        
        logger.info("Creating/updating vector store...")
        docsearch = create_or_load_vectorstore(chunks, embeddings)
        
        logger.info("Index created/updated successfully!")
        
    except Exception as e:
        logger.error(f"Error creating index: {e}")
        raise

if __name__ == "__main__":
    main()
