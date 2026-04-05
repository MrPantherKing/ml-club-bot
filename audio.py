# ─────────────────────────────────────────────
#  audio.py  —  TTS Audio System
#  Edge TTS (online) with pyttsx3 fallback (offline)
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


class AudioSystem:
    def __init__(self):
        self.speaking       = False
        self._queue         = queue.Queue()
        self._stop_event    = threading.Event()
        self._worker        = None
        self._edge_ok       = True
        self._pyttsx        = None

        self._init_pyttsx()
        self._init_mixer()
        self._start_worker()

    # ── init ──────────────────────────────────────────────────
    def _init_pyttsx(self):
        try:
            self._pyttsx = pyttsx3.init()
            voices = self._pyttsx.getProperty('voices')
            print(f"[Audio] {len(voices)} voices available")
            preferred = [
                'Microsoft Zira Desktop',
                'Microsoft Hazel Desktop',
                'Microsoft Susan Desktop',
                'Microsoft David Desktop',
            ]
            chosen = None
            for v in voices:
                for p in preferred:
                    if p.lower() in v.name.lower():
                        chosen = v
                        break
                if chosen:
                    break

            if chosen:
                self._pyttsx.setProperty('voice', chosen.id)
                print(f"[Audio] pyttsx3 voice: {chosen.name}")
            self._pyttsx.setProperty('rate',   150)
            self._pyttsx.setProperty('volume', 0.9)
        except Exception as e:
            print(f"[Audio] pyttsx3 init failed: {e}")
            self._pyttsx = None

    def _init_mixer(self):
        try:
            # Pre-init BEFORE pygame.init() equivalent to avoid exclusive-mode grab.
            # 44100 Hz is the standard shared-mode rate on Windows – matching it
            # prevents WASAPI from kicking screen-recorders off the audio device.
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(8)
            print("[Audio] Mixer ready (44100 Hz shared-mode)")
        except Exception as e:
            print(f"[Audio] Mixer init failed: {e}")

    def _start_worker(self):
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    # ── worker ────────────────────────────────────────────────
    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                text = self._queue.get(timeout=0.1)
                if text:
                    self._speak_sync(text)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Audio] Worker error: {e}")

    # ── Edge TTS ──────────────────────────────────────────────
    async def _edge_get(self, text: str):
        try:
            comm = edge_tts.Communicate(text, "en-US-AriaNeural")
            data = b""
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    data += chunk["data"]
            if not data:
                return None
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(data)
                return f.name
        except Exception as e:
            print(f"[Audio] Edge TTS error: {e}")
            return None

    # ── speak ─────────────────────────────────────────────────
    def _speak_sync(self, text: str):
        if not text.strip():
            return
        self.speaking = True
        tmp = None
        try:
            if self._edge_ok:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    tmp  = loop.run_until_complete(self._edge_get(text))
                    loop.close()

                    if tmp and os.path.exists(tmp):
                        pygame.mixer.music.load(tmp)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            time.sleep(0.05)
                        pygame.mixer.music.stop()
                        pygame.mixer.music.unload()   # release file handle immediately
                        return

                except Exception as e:
                    print(f"[Audio] Edge failed: {e}")
                    self._edge_ok = False

            # Fallback
            if self._pyttsx:
                try:
                    self._pyttsx.say(text)
                    self._pyttsx.runAndWait()
                    return
                except Exception as e:
                    print(f"[Audio] pyttsx3 failed: {e}")

            print(f"[Audio] Could not speak: {text}")

        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except Exception:
                    pass
            self.speaking = False

    # ── public API ────────────────────────────────────────────
    def speak_text(self, text: str):
        if text and text.strip():
            self._queue.put(text)

    def is_speaking(self) -> bool:
        return self.speaking

    def stop(self):
        self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=1)
        try:
            pygame.mixer.quit()
        except Exception:
            pass
