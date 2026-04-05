# ─────────────────────────────────────────────
#  robust_voice.py  —  ACTUALLY WORKING VOICE
# ─────────────────────────────────────────────

import speech_recognition as sr
import threading
import time
from typing import Optional, Callable


class RobustVoiceInput:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_listening = False
        self._voice_callback = None
        self._stop_event = threading.Event()
        self._listening_thread = None
        
        # Very sensitive settings
        self.recognizer.energy_threshold = 100  # Very low threshold
        self.recognizer.pause_threshold = 0.5   # Short pause
        self.recognizer.dynamic_energy_threshold = False  # Disable dynamic
        self.recognizer.operation_timeout = None  # No timeout
        
        self._init_microphone()

    def _init_microphone(self):
        """Initialize microphone"""
        try:
            # Try to use the first available microphone
            mics = sr.Microphone.list_microphone_names()
            print(f"[Voice] Available mics: {len(mics)}")
            
            # Use default microphone
            self.microphone = sr.Microphone()
            
            with self.microphone as source:
                print("[Voice] Calibrating...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                # Override with very low threshold
                self.recognizer.energy_threshold = 100
                
            print(f"[Voice] Ready! Threshold: {self.recognizer.energy_threshold}")
            
        except Exception as e:
            print(f"[Voice] Mic error: {e}")

    def set_voice_callback(self, callback: Callable[[str], None]):
        """Set callback for recognized speech"""
        self._voice_callback = callback

    def start_listening(self):
        """Start continuous listening"""
        if not self.microphone or self.is_listening:
            return False
            
        self.is_listening = True
        self._stop_event.clear()
        self._listening_thread = threading.Thread(target=self._continuous_listen, daemon=True)
        self._listening_thread.start()
        print("[Voice] Continuous listening started...")
        return True

    def stop_listening(self):
        """Stop listening"""
        self._stop_event.set()
        self.is_listening = False
        print("[Voice] Listening stopped")

    def _continuous_listen(self):
        """Continuous listening without timeouts"""
        while not self._stop_event.is_set():
            try:
                print("[Voice] Listening continuously...")
                with self.microphone as source:
                    # Listen without timeout - this is the key!
                    audio = self.recognizer.listen(source, phrase_time_limit=5)
                
                print("[Voice] Got audio, recognizing...")
                
                # Try Google first
                text = None
                try:
                    text = self.recognizer.recognize_google(audio)
                    print(f"[Google] Heard: {text}")
                except sr.UnknownValueError:
                    print("[Google] No speech detected")
                except sr.RequestError as e:
                    print(f"[Google] Error: {e}")
                
                # Try Sphinx if Google fails
                if not text:
                    try:
                        text = self.recognizer.recognize_sphinx(audio)
                        print(f"[Sphinx] Heard: {text}")
                    except sr.UnknownValueError:
                        print("[Sphinx] No speech detected")
                    except sr.RequestError as e:
                        print(f"[Sphinx] Error: {e}")
                
                # Process the result
                if text and len(text.strip()) > 1:
                    print(f"[Voice] SUCCESS: {text.strip()}")
                    if self._voice_callback:
                        self._voice_callback(text.strip())
                        
            except sr.WaitTimeoutError:
                # This shouldn't happen with no timeout, but just in case
                continue
            except Exception as e:
                print(f"[Voice] Error: {e}")
                time.sleep(0.1)  # Brief pause before retrying

    def is_available(self):
        """Check if microphone is available"""
        return self.microphone is not None

    def is_active(self):
        """Check if listening"""
        return self.is_listening
