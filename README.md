# Bot Performance System

A synchronized system of timing + control + illusion.

---

## Setup

```bash
pip install -r requirements.txt
python main.py
```

---

## Keyboard Controls (Hidden During Demo)

| Key     | Action              |
|---------|---------------------|
| `SPACE` | Start (IDLE → WAKE) |
| `T`     | Force TALKING       |
| `F`     | Force FINAL         |
| `B`     | Force BURST         |
| `R`     | Reset to IDLE       |
| `ESC`   | Quit                |

---

## State Flow

```
IDLE → WAKE → TALKING → FINAL → BURST → POSTER
```

- **IDLE** — bot floats gently, blinking
- **WAKE** — bot scales up (1.8s), anticipation builds
- **TALKING** — ML classifies input → TTS speaks → mouth animates
- **FINAL** — 1.4s dramatic pause, nothing moves
- **BURST** — glitch sound + screen shake + white flash → bot vanishes
- **POSTER** — your poster fades in cleanly

---

## Swapping Placeholders

### 1. Add Your Poster
Drop your file here:
```
assets/poster.png
```
That's it. The system loads it automatically.

### 2. Add a Sprite Sheet
1. Place your sheet at `assets/sprites/bot_sheet.png`
2. In `config.py`, set:
```python
USE_SPRITE_SHEET = True
SPRITE_FRAME_W   = 128   # your frame width
SPRITE_FRAME_H   = 128   # your frame height
SPRITE_COLS      = 4     # frames per row
# Row layout:
SPRITE_ROW_IDLE  = 0
SPRITE_ROW_TALK  = 1
SPRITE_ROW_BLINK = 2
```

### 3. Add Real Audio Files
1. Place `.wav` files in `assets/audio/`
2. In `config.py`, set:
```python
USE_REAL_AUDIO = True
AUDIO_FILES = {
    "greeting":    "greeting.wav",
    "invitation":  "invitation.wav",
    "explanation": "explanation.wav",
    "closing":     "closing.wav",
}
```

### 4. Control Which Intent Fires
In `config.py`, change:
```python
DEMO_INPUT = "welcome everyone, let's begin the session"
```
This input is silently passed to the ML classifier during TALKING.
Change it to route to whichever intent you want.

### 5. Change the Script Lines
In `config.py`:
```python
SCRIPTS = {
    "greeting":    "Hello everyone. Welcome to today's demonstration.",
    "invitation":  "I invite you all to witness what we have built together.",
    "explanation": "This system combines machine learning with real-time performance.",
    "closing":     "And that is how the future of intelligent systems looks.",
}
```

### 6. Tune Timings
All in `config.py`:
```python
T_WAKE_DURATION  = 1.8   # anticipation phase
T_FINAL_PAUSE    = 1.4   # dramatic beat before burst
T_BURST_FLASH    = 0.35  # flash duration
T_POSTER_FADEIN  = 1.0   # poster reveal speed
```

---

## File Structure

```
bot_system/
├── main.py              # game loop + HUD + input
├── state_machine.py     # director — controls all transitions
├── animation.py         # visual layer — bot drawing + effects
├── audio.py             # TTS / real audio + glitch sound
├── ml_classifier.py     # intent classifier (trains at startup)
├── config.py            # all settings in one place
├── requirements.txt
└── assets/
    ├── poster.png        ← drop your poster here
    ├── sprites/
    │   └── bot_sheet.png ← drop your sprite sheet here
    └── audio/
        ├── greeting.wav  ← drop your audio files here
        └── ...
```
