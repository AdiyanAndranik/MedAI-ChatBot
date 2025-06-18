import os
import langid
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec
from deep_translator import GoogleTranslator
import functools
import time

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
index_name = "med-chat-index"

@functools.lru_cache(maxsize=1)
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}, 
        encode_kwargs={'batch_size': 64}
    )

@functools.lru_cache(maxsize=100)
def detect_language(text):
    try:
        if not text or len(text.strip()) < 3:
            return "en"
        
        armenian_chars = sum(1 for c in text if '\u0530' <= c <= '\u058F')
        cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        
        if armenian_chars > len(text) * 0.3:
            return "hy"
        elif cyrillic_chars > len(text) * 0.3:
            return "ru"
        
        langid.set_languages(['hy', 'ru', 'en'])
        lang, confidence = langid.classify(text)
        return lang if confidence > 0.7 else "en"
    except:
        return "en"

def translate_text(text, target_lang, source_lang="auto", max_retries=2):
    if not text or not text.strip() or target_lang == source_lang:
        return text
    
    for attempt in range(max_retries):
        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            result = translator.translate(text)
            return result if result else text
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Translation failed after {max_retries} attempts: {e}")
                return text
            time.sleep(0.1)
    
    return text

def load_documents(data_path):
    loader = DirectoryLoader(data_path, glob="*.pdf", loader_cls=PyPDFLoader)
    return loader.load()

def split_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    return splitter.split_documents(docs)

def create_or_load_vectorstore(text_chunks, embeddings):
    pc = Pinecone(api_key=PINECONE_API_KEY)
    existing_indexes = pc.list_indexes().names()
    
    if index_name not in existing_indexes:
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )

        texts = [t.page_content for t in text_chunks]
        PineconeVectorStore.from_texts(
            texts,
            embedding=embeddings,
            index_name=index_name,
            batch_size=64
        )
    
    return PineconeVectorStore.from_existing_index(index_name, embeddings)