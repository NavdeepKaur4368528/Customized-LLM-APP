import gradio as gr
from huggingface_hub import InferenceClient
from typing import List, Tuple
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer, util
import numpy as np
import faiss

client = InferenceClient("HuggingFaceH4/zephyr-7b-beta")

# Placeholder for the app's state
class MyApp:
    def __init__(self) -> None:
        self.documents = []
        self.embeddings = None
        self.index = None
        self.load_pdf("emily_post_etiquette.pdf")  # Replace with the actual PDF filename
        self.build_vector_db()

    def load_pdf(self, file_path: str) -> None:
        """Extracts text from a PDF file and stores it in the app's documents."""
        doc = fitz.open(file_path)
        self.documents = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            self.documents.append({"page": page_num + 1, "content": text})
        print("PDF processed successfully!")

    def build_vector_db(self) -> None:
        """Builds a vector database using the content of the PDF."""
        model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embeddings = model.encode([doc["content"] for doc in self.documents])
        self.index = faiss.IndexFlatL2(self.embeddings.shape[1])
        self.index.add(np.array(self.embeddings))
        print("Vector database built successfully!")

    def search_documents(self, query: str, k: int = 3) -> List[str]:
        """Searches for relevant documents using vector similarity."""
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = model.encode([query])
        D, I = self.index.search(np.array(query_embedding), k)
        results = [self.documents[i]["content"] for i in I[0]]
        return results if results else ["No relevant documents found."]

app = MyApp()

def respond(
    message: str,
    history: List[Tuple[str, str]],
    system_message: str,
    max_tokens: int,
    temperature: float,
    top_p: float,
):
    system_message = "You are a knowledgeable and friendly etiquette coach based on Emily Post's guide to modern manners. You provide helpful advice on good manners, social etiquette, and proper behavior in various situations. You are concise, polite, and always respond like a human expert would. You ask one question at a time when clarification is needed. Remember to be respectful and considerate in your responses. Use the etiquette guide to provide accurate and helpful information on manners and social norms."
    messages = [{"role": "system", "content": system_message}]

    for val in history:
        if val[0]:
            messages.append({"role": "user", "content": val[0]})
        if val[1]:
            messages.append({"role": "assistant", "content": val[1]})

    messages.append({"role": "user", "content": message})

    # RAG - Retrieve relevant documents
    retrieved_docs = app.search_documents(message)
    context = "\n".join(retrieved_docs)
    messages.append({"role": "system", "content": "Relevant information: " + context})

    response = ""
    for message in client.chat_completion(
        messages,
        max_tokens=100,
        stream=True,
        temperature=0.7,
        top_p=0.9,
    ):
        token = message.choices[0].delta.content
        response += token
        yield response

demo = gr.Blocks()

with demo:
    gr.Markdown(
        "‼️Disclaimer: This chatbot is based on Emily Post's Etiquette guide and is intended for general advice on good manners and social etiquette.‼️"
    )
    
    chatbot = gr.ChatInterface(
        respond,
        examples=[
            ["How should I set a formal dinner table?"],
            ["What's the proper way to introduce people?"],
            ["How do I write a thank-you note?"],
            ["How do I politely decline an invitation?"],
            ["What are some tips for being a good houseguest?"],
            ["How should I behave at a business lunch?"],
            ["What's the etiquette for using mobile phones in public?"]
        ],
        title='Good Manners Assistant 🎩🍽️'
    )

if __name__ == "__main__":
    demo.launch()