from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, AIMessage
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

memory = ConversationBufferMemory(
    memory_key="chat_history",
    input_key="question",
    return_messages=True
)

def format_chat_history(history):
    if not history:
        return "No previous conversation."
    
    recent_history = history[-4:] if len(history) > 4 else history
    formatted = ""
    for message in recent_history:
        if isinstance(message, HumanMessage):
            formatted += f"User: {message.content}\n"
        elif isinstance(message, AIMessage):
            formatted += f"Assistant: {message.content}\n"
    return formatted.strip()

def format_docs(docs):
    if not docs:
        return "No relevant context found."
    
    doc_content = docs[0].page_content if docs else ""
    return doc_content[:800] + "..." if len(doc_content) > 800 else doc_content

prompt_template = """
You are a professional medical AI assistant specializing in providing accurate, detailed, and well-structured answers based on the provided context and conversation history.

When responding to medical questions:
1. Structure your answers with clear sections and numerical points when listing symptoms, treatments, or steps
2. Use bullet points or numbered lists for clarity when appropriate
3. Organize information in a logical sequence (e.g., definition → causes → symptoms → treatments)
4. Include relevant medical terminology with plain language explanations
5. Provide comprehensive explanations while remaining concise
6. When discussing treatments or recommendations, clearly separate them into categories (e.g., lifestyle changes, medications, when to see a doctor)
7. Use professional medical language while ensuring the information is accessible

Use the conversation history to understand the context of the current question, ensuring responses are relevant to previous questions (e.g., if the user asked about arthritis, assume follow-up questions like "How to treat it?" refer to arthritis).

If the context is insufficient, use general medical knowledge, state assumptions, or suggest consulting a doctor. Always prioritize clarity, safety, and relevance.

Conversation History:
{chat_history}

Context from Documents:
{context}

Current Question:
{question}

Answer in English (it will be translated to the user's language if needed). Format your response professionally with appropriate structure:
"""

PROMPT = PromptTemplate(template=prompt_template, input_variables=["chat_history", "context", "question"])