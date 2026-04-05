# ─────────────────────────────────────────────
#  ollama_client.py  —  Ollama Integration
#  Handles conversational AI responses using Ollama
# ─────────────────────────────────────────────

import ollama
import threading
import time
from typing import Optional, Callable


class OllamaClient:
    def __init__(self, model_name: str = "llama3.2:1b"):
        """
        Initialize Ollama client with specified model.
        Default: llama3.2:1b (available model)
        """
        self.model_name = model_name
        self.conversation_history = []
        self.is_responding = False
        self._response_thread = None
        self._callback = None
        
        # Test connection
        try:
            ollama.list()
            print(f"[Ollama] Connected successfully, using model: {model_name}")
        except Exception as e:
            print(f"[Ollama] Connection failed: {e}")
            print("[Ollama] Make sure Ollama is running locally")

    def set_response_callback(self, callback: Callable[[str], None]):
        """Set callback function to handle AI responses"""
        self._callback = callback

    def add_system_message(self, message: str):
        """Add a system message to define AI behavior"""
        self.conversation_history.append({
            "role": "system",
            "content": message
        })

    def send_user_message(self, message: str) -> bool:
        """
        Send user message to Ollama and get response.
        Returns True if message was sent successfully.
        """
        if self.is_responding:
            print("[Ollama] Already responding, please wait...")
            return False

        # Add user message to conversation
        self.conversation_history.append({
            "role": "user",
            "content": message
        })

        # Start response in separate thread
        self._response_thread = threading.Thread(
            target=self._get_response,
            daemon=True
        )
        self._response_thread.start()
        return True

    def _get_response(self):
        """Get response from Ollama in background thread"""
        self.is_responding = True
        
        try:
            print("[Ollama] Thinking...")
            response = ollama.chat(
                model=self.model_name,
                messages=self.conversation_history
            )
            
            ai_message = response['message']['content']
            
            # Add AI response to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": ai_message
            })
            
            print(f"[Ollama] Response: {ai_message[:100]}...")
            
            # Call callback if set
            if self._callback:
                self._callback(ai_message)
                
        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            print(f"[Ollama] Error: {e}")
            if self._callback:
                self._callback(error_msg)
        
        finally:
            self.is_responding = False

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("[Ollama] Conversation history cleared")

    def is_busy(self) -> bool:
        """Check if AI is currently responding"""
        return self.is_responding

    def get_last_response(self) -> Optional[str]:
        """Get the last AI response from conversation history"""
        for msg in reversed(self.conversation_history):
            if msg["role"] == "assistant":
                return msg["content"]
        return None
