# ─────────────────────────────────────────────
#  premium_audio.py  —  HIGH-QUALITY TTS SYSTEM
# ─────────────────────────────────────────────

import pygame
import threading
import time
import queue
import asyncio
import edge_tts
import pyttsx3
import tempfile
import os
from typing import Optional


class PremiumAudioSystem:
    def __init__(self):
        self.speaking = False
        self._speech_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_thread = None
        self._edge_available = True
        self._pyttsx_engine = None
        
        # Initialize systems
        self._init_pyttsx()
        self._init_pygame()
        self._start_worker()

    def _init_pyttsx(self):
        """Initialize pyttsx3 as fallback"""
        try:
            self._pyttsx_engine = pyttsx3.init()
            
            # Find the best female voice
            voices = self._pyttsx_engine.getProperty('voices')
            best_voice = None
            voice_priority = [
                'Microsoft Zira Desktop',
                'Microsoft Hazel Desktop', 
                'Microsoft Susan Desktop',
                'Microsoft David Desktop'  # Fallback male voice
            ]
            
            print(f"[Audio] Available voices: {len(voices)}")
            for voice in voices:
                print(f"[Audio] Voice: {voice.name}")
                for priority in voice_priority:
                    if priority.lower() in voice.name.lower():
                        best_voice = voice
                        print(f"[Audio] Selected voice: {voice.name}")
                        break
                if best_voice:
                    break
            
            if best_voice:
                self._pyttsx_engine.setProperty('voice', best_voice.id)
                print(f"[Audio] pyttsx3 voice: {best_voice.name}")
            else:
                print("[Audio] Using default pyttsx3 voice")
            
            # Set natural speech parameters
            self._pyttsx_engine.setProperty('rate', 150)  # Natural speed
            self._pyttsx_engine.setProperty('volume', 0.9)
            
        except Exception as e:
            print(f"[Audio] pyttsx3 init failed: {e}")
            self._pyttsx_engine = None

    def _init_pygame(self):
        """Initialize pygame mixer"""
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            print("[Audio] Pygame mixer initialized for high quality")
        except Exception as e:
            print(f"[Audio] Pygame init failed: {e}")

    def _start_worker(self):
        """Start the speech worker thread"""
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()

    def _speech_worker(self):
        """Worker thread for processing speech"""
        while not self._stop_event.is_set():
            try:
                text = self._speech_queue.get(timeout=0.1)
                if text:
                    self._speak_text_sync(text)
                self._speech_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Audio] Speech error: {e}")

    async def _get_edge_audio(self, text):
        """Get audio from Edge TTS"""
        try:
            # Use high-quality female voice
            voice = "en-US-AriaNeural"  # Very natural female voice
            
            communicate = edge_tts.Communicate(text, voice)
            
            # Get audio data correctly
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            if not audio_data:
                print("[Audio] No audio data received from Edge TTS")
                return None
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                return tmp_file.name
                
        except Exception as e:
            print(f"[Audio] Edge TTS error: {e}")
            return None

    def _speak_text_sync(self, text):
        """Speak text using best available TTS"""
        if not text.strip():
            return
            
        self.speaking = True
        temp_file = None
        
        try:
            # Try Edge TTS first (highest quality)
            if self._edge_available:
                try:
                    # Run async function in sync context
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    temp_file = loop.run_until_complete(self._get_edge_audio(text))
                    loop.close()
                    
                    if temp_file and os.path.exists(temp_file):
                        # Play with pygame
                        pygame.mixer.music.load(temp_file)
                        pygame.mixer.music.play()
                        
                        # Wait for playback to complete
                        while pygame.mixer.music.get_busy():
                            time.sleep(0.1)
                        
                        print(f"[Audio] Edge TTS: {text[:30]}...")
                        return
                        
                except Exception as e:
                    print(f"[Audio] Edge TTS failed: {e}")
                    self._edge_available = False
            
            # Fallback to pyttsx3
            if self._pyttsx_engine:
                try:
                    self._pyttsx_engine.say(text)
                    self._pyttsx_engine.runAndWait()
                    print(f"[Audio] pyttsx3: {text[:30]}...")
                    return
                except Exception as e:
                    print(f"[Audio] pyttsx3 failed: {e}")
            
            print(f"[Audio] Could not speak: {text}")
            
        except Exception as e:
            print(f"[Audio] Speech error: {e}")
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass
            
            self.speaking = False

    def speak_text(self, text):
        """Queue text for speaking"""
        if text and text.strip():
            self._speech_queue.put(text)

    def is_speaking(self):
        """Check if currently speaking"""
        return self.speaking

    def stop(self):
        """Stop audio system"""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=1)
        pygame.mixer.quit()
