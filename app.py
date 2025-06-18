from flask import Flask, render_template, jsonify, request, Response
from medAI.config import get_embeddings, detect_language, translate_text
from medAI.prompt import PROMPT, memory, format_chat_history, format_docs
from langchain_pinecone import PineconeVectorStore
from dotenv import load_dotenv
import os
import sys
import logging
from cachetools import TTLCache
import pinecone
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import django
from django.conf import settings
from huggingface_hub import InferenceClient

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_auth.settings')
django.setup()

from authentication.models import ChatSession, ChatMessage, UserProfile
from django.contrib.auth.models import User

logging.basicConfig(level=logging.INFO, format="[%(asctime)s]: %(message)s:")
logger = logging.getLogger(__name__)

cache = TTLCache(maxsize=500, ttl=7200)
translation_cache = TTLCache(maxsize=200, ttl=3600)

embeddings = None
docsearch = None
llm = None
chain = None
executor = ThreadPoolExecutor(max_workers=2)

class MixtralLLM:
    def __init__(self, model_name="mistralai/Mixtral-8x7B-Instruct-v0.1", api_token=None):
        self.model_name = model_name
        self.client = InferenceClient(
            provider="together",
            api_key=api_token
        )

    def __call__(self, prompt):
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1024,
                temperature=0.7,
                top_p=0.9
            )
            
            return completion.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Mixtral API error: {str(e)}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again in a moment."
    
    def stream(self, prompt):
        """Stream response word by word"""
        response = self(prompt)
        if response:
            words = response.split()
            for word in words:
                yield word + " "
                time.sleep(0.05)

def initialize_components():
    global embeddings, docsearch, llm, chain
    
    if embeddings is None:
        logger.info("Initializing embeddings...")
        embeddings = get_embeddings()

    if docsearch is None:
        logger.info("Initializing vector store...")
        try:
            pc = pinecone.Pinecone(api_key=PINECONE_API_KEY)
            if pc.describe_index(index_name).status['ready']:
                docsearch = PineconeVectorStore.from_existing_index(index_name, embeddings)
            else:
                raise Exception("Index not ready or does not exist.")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            raise
    
    if llm is None:
        logger.info("Initializing Mixtral LLM...")
        llm = MixtralLLM(
            model_name="mistralai/Mixtral-8x7B-Instruct-v0.1",
            api_token=os.getenv("HUGGINGFACE_TOKEN")
        )
    
    if chain is None:
        logger.info("Initializing chain with Mixtral...")
        retriever = docsearch.as_retriever(search_kwargs={'k': 2})
        
        def create_chain_response(query):
            try:
                docs = retriever.get_relevant_documents(query)
                context = format_docs(docs)
                
                chat_history = format_chat_history(memory.load_memory_variables({})["chat_history"])
                
                formatted_prompt = PROMPT.format(
                    context=context,
                    chat_history=chat_history,
                    question=query
                )

                response = llm(formatted_prompt)
                return response
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                return "I'm sorry, something went wrong while generating the response."

        chain = create_chain_response

def save_message_to_db(user_id, message, response, language='en'):
    """Save chat message to Django database"""
    try:
        if user_id:
            user = User.objects.get(id=user_id)
            session, created = ChatSession.objects.get_or_create(
                user=user,
                defaults={'session_id': f"session_{user_id}_{int(time.time())}"}
            )
            
            ChatMessage.objects.create(
                session=session,
                message=message,
                response=response,
                language=language
            )
            logger.info(f"Message saved to database for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving message to database: {str(e)}")

def get_user_from_session(request):
    """Get user ID from session cookie"""
    try:
        session_key = request.cookies.get('sessionid')
        if session_key:
            from django.contrib.sessions.models import Session
            from django.contrib.auth.models import User
            session = Session.objects.get(session_key=session_key)
            user_id = session.get_decoded().get('_auth_user_id')
            if user_id:
                return User.objects.get(id=user_id)
    except Exception as e:
        logger.error(f"Error getting user from session: {str(e)}")
    return None

app = Flask(__name__)

load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
index_name = "med-chat-index"

def init_app():
    try:
        logger.info("Pre-initializing components for faster first response...")
        initialize_components()
        logger.info("Components initialized successfully!")
    except Exception as e:
        logger.error(f"Error initializing components: {str(e)}")

with app.app_context():
    init_app()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/api/user-info", methods=["GET"])
def get_user_info():
    """Get user information for the chat interface"""
    try:
        is_guest = request.args.get('guest') == 'true'
        
        if is_guest:
            return jsonify({
                'authenticated': False,
                'guest': True,
                'user': {
                    'name': 'Guest User',
                    'id': None
                }
            })

        user = get_user_from_session(request)
        
        if user:
            return jsonify({
                'authenticated': True,
                'guest': False,
                'user': {
                    'name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            })
        else:
            return jsonify({
                'authenticated': False,
                'guest': True,
                'user': {
                    'name': 'Guest User',
                    'id': None
                }
            })
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        return jsonify({
            'authenticated': False,
            'guest': True,
            'user': {
                'name': 'Guest User',
                'id': None
            }
        })

@app.route("/get", methods=["POST"])
def chat():
    try:
        msg = request.form["msg"].strip()
        if not msg:
            return jsonify({"error": "Empty message"}), 400

        start_time = time.time()
        input_lang = detect_language(msg)
        logger.info(f"Detected input language: {input_lang}")

        user = get_user_from_session(request)
        user_id = user.id if user else None

        cache_key = f"{msg.lower().strip()}_{input_lang}"
        if cache_key in cache:
            logger.info(f"Cache hit for query: {msg}")
            cached_response = cache[cache_key]

            if user_id:
                save_message_to_db(user_id, msg, cached_response, input_lang)
            
            def stream_cached():
                for word in cached_response.split():
                    yield f"data: {json.dumps({'word': word + ' '})}\n\n"
                    time.sleep(0.03)
                yield f"data: {json.dumps({'complete': True, 'full_response': cached_response})}\n\n"
            
            return Response(stream_cached(), mimetype='text/plain')

        initialize_components()

        query = msg
        translation_future = None
        if input_lang in ["hy", "ru"]:
            translation_future = executor.submit(translate_text, msg, "en")

        def generate_response():
            try:
                nonlocal query

                if translation_future:
                    query = translation_future.result(timeout=5)
                    logger.info(f"Translated query: {query}")

                logger.info(f"Processing query: {query}")
                english_response = chain(query)

                final_response = english_response
                if input_lang in ["hy", "ru"]:
                    final_response = translate_text(english_response, input_lang)

                for word in final_response.split():
                    yield f"data: {json.dumps({'word': word + ' '})}\n\n"
                    time.sleep(0.05)

                memory.save_context({"question": msg}, {"result": final_response})
                cache[cache_key] = final_response

                if user_id:
                    save_message_to_db(user_id, msg, final_response, input_lang)

                logger.info(f"Response time: {time.time() - start_time:.2f}s")
                yield f"data: {json.dumps({'complete': True, 'full_response': final_response})}\n\n"
            except Exception as e:
                logger.error(f"Error in response generation: {str(e)}")
                error_msg = "An error occurred. Please try again later."
                if input_lang in ["hy", "ru"]:
                    error_msg = translate_text(error_msg, input_lang)
                yield f"data: {json.dumps({'error': error_msg})}\n\n"

        return Response(generate_response(), mimetype='text/plain')

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/reset", methods=["POST"])
def reset_chat():
    try:
        memory.clear()
        cache.clear()
        translation_cache.clear()
        return jsonify({"message": "Chat history reset."})
    except Exception as e:
        logger.error(f"Reset error: {str(e)}")
        return jsonify({"error": "Failed to reset chat."}), 500

@app.route("/api/chat-history", methods=["GET"])
def get_chat_history():
    """Get chat history for authenticated users"""
    try:
        user = get_user_from_session(request)
        if not user:
            return jsonify({"error": "User not authenticated"}), 401
        
        sessions = ChatSession.objects.filter(user=user).order_by('-updated_at')[:5]
        
        history = []
        for session in sessions:
            messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
            session_data = {
                'session_id': session.session_id,
                'title': session.title,
                'created_at': session.created_at.isoformat(),
                'messages': [
                    {
                        'message': msg.message,
                        'response': msg.response,
                        'timestamp': msg.timestamp.isoformat(),
                        'language': msg.language
                    }
                    for msg in messages
                ]
            }
            history.append(session_data)
        
        return jsonify({"history": history})
        
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        return jsonify({"error": "Failed to get chat history"}), 500

@app.route("/test", methods=["GET"])
def test_endpoint():
    """Simple test endpoint to verify the Flask app is working"""
    return jsonify({
        "status": "Flask app is working!",
        "model": "Mixtral-8x7B-Instruct-v0.1",
        "method": request.method,
        "timestamp": time.time()
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
