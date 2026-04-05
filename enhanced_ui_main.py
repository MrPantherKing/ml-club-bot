# enhanced_ui_main.py — ML Club AI Bot │ Modern Full UI
import sys, time, math, random, threading, requests, json
import pygame, pygame.gfxdraw

from audio import AudioSystem
from robust_voice import RobustVoiceInput
from ui_systems import (Aurora, NeuralBG, Orbits, Pulses, ScanLine,
                        Waveform, ChatPanel, Confetti, FloatDots,
                        lerp3, ease_out, grad_h, glow_c, glass_panel, jbmono)

# ── Sizes ──────────────────────────────────────────────────────────
WIN_W,  WIN_H  = 1280, 720
FPS = 60

# ── Palette ────────────────────────────────────────────────────────
BG    = (8,   10,  22);  BG2   = (12,  15,  32)
BLUE  = (74,  158, 255); PURP  = (180,  78, 255)
CYAN  = (45,  210, 255); GREEN = (80,  220, 140)
ORANGE= (255, 165,  60); RED   = (255,  80,  80)
WHITE = (255, 255, 255); MUTED = (70,   80, 125)

# Bot palette
HL, HR = (68, 85, 200), (92, 60, 192)
EC = (52, 68, 180);   VC = (245, 248, 255)
EL, ER2= (76,110,215),(70, 55,186)
AL, AR = (45,165,225),(128,52,198)
SC     = (60, 78, 185)
CLOUD_COL = [(52,182,220),(56,158,218),(62,134,212),(68,112,208),
             (74,92,200),(82,73,193),(88,58,186),(78,52,175),(65,46,160)]

# ── App states ─────────────────────────────────────────────────────
IDLE   = "IDLE"
ACT1   = "ACT1"   # Opening speech
ACT2   = "ACT2"   # Invitation (come to dais)
ACT3   = "ACT3"   # Request to say reveal
ACT4   = "ACT4"   # Dramatic countdown  3…2…1…
POSTER = "POSTER" # Poster on screen + confetti
CHAT   = "CHAT"   # AI Q&A mode


# ═══════════════════════════════════════════════════════════════════
#  Pixel cloud builder
# ═══════════════════════════════════════════════════════════════════
def _build_cloud(cx, cy):
    rng = random.Random(2024)
    items = []
    ox, oy = cx + 95, cy - 85
    columns = [
        (  8, [-16,-34,-53,-72,-92,-112,-132], 15, 0),
        ( -8, [-18,-38,-58,-78,-98,-118],      14, 0),
        (-28, [-22,-44,-67,-90,-112],           13, 1),
        (-50, [-28,-55,-82,-108],               11, 2),
        (-72, [-35,-65,-96],                    10, 3),
        (-94, [-42,-78],                         9, 3),
        (-116,[-52,-88],                         8, 4),
        (-138,[-62],                             7, 5),
        (-160,[-72],                             6, 5),
    ]
    for dx, dy_list, sz, ci in columns:
        for dy in dy_list:
            items.append({'bx':ox+dx+rng.uniform(-2,2),
                          'by':oy+dy+rng.uniform(-2,2),
                          'x':0,'y':0,'sz':sz,'sq':True,
                          'col':CLOUD_COL[ci],'ba':232,
                          'ph':rng.uniform(0,6.28),'sp':rng.uniform(.2,.7),'ca':232})
    for _ in range(95):
        dx = rng.uniform(-40,-240); dy = rng.uniform(-40,-170)
        dist = math.sqrt(dx*dx+dy*dy); norm = min(dist/200,1.0)
        sz = max(1,int((1-norm)*8+1)); sq = sz>=5; ci = min(int(norm*6)+3,8)
        items.append({'bx':ox+dx,'by':oy+dy,'x':0,'y':0,'sz':sz,'sq':sq,
                      'col':CLOUD_COL[ci],'ba':max(70,int(210*(1-norm*.55))),
                      'ph':rng.uniform(0,6.28),'sp':rng.uniform(.1,.5),'ca':100})
    return items


# ═══════════════════════════════════════════════════════════════════
#  Bot renderer
# ═══════════════════════════════════════════════════════════════════
class MLClubBot:
    HW, HH = 95, 85
    HR_  = 14
    EW, EH, ER_ = 24, 92, 9
    VW, VH, VR  = 152, 68, 28
    EYEW, EYEGAP, EYEYR = 36, 28, -10
    # Antennas: emerge from mid-upper EAR panels, angle outward+up (matches image)
    ANT_LB = (-108, -38)  # left base  – on left ear, upper-mid
    ANT_LT = (-165, -110) # left tip   – upper-left
    ANT_RB = ( 108, -40)  # right base – on right ear, upper-mid
    ANT_RT = ( 148, -108) # right tip  – upper-right

    # Expression states
    EXPR_IDLE     = 0
    EXPR_HAPPY    = 1
    EXPR_THINKING = 2
    EXPR_LISTENING= 3

    def __init__(self, screen, cx, cy):
        self.screen = screen
        self.cx, self.cy = cx, cy
        self.t = 0.0; self.float_y = 0.0
        self.blink_t = 0.0; self.blinking = False
        self.mouth_open = 0.0; self.speaking = False
        self.glow_v = 0.1
        self.expr = self.EXPR_IDLE
        self.expr_t = 0.0       # timer for expression transitions
        self.think_wave = 0.0   # thinking mouth wave
        self.cloud = _build_cloud(cx, cy)

    def update(self, dt, voice_on, speaking, state=None):
        self.t += dt; self.speaking = speaking
        self.float_y = math.sin(self.t*1.4)*7 + math.sin(self.t*2.8)*2.5
        self.expr_t += dt
        self.think_wave = math.sin(self.t * 6)

        # Decide expression based on app state
        if speaking:
            self.expr = self.EXPR_IDLE   # mouth handles it
        elif voice_on:
            self.expr = self.EXPR_LISTENING
        elif state == ACT1:              # excited opening
            self.expr = self.EXPR_HAPPY
        elif state in (ACT2, ACT3):      # formal/countdown
            self.expr = self.EXPR_IDLE
        else:
            self.expr = self.EXPR_IDLE

        self.blink_t += dt
        if self.blink_t > random.uniform(3.5,5.5): self.blinking = True
        if self.blinking and self.blink_t > 0.14: self.blinking = False; self.blink_t = 0.0
        if speaking:
            self.mouth_open = abs(math.sin(self.t*14))*.6 + abs(math.sin(self.t*7))*.4
        else:
            self.mouth_open = max(0, self.mouth_open - dt*5)
        self.glow_v = (0.5+0.5*abs(math.sin(self.t*4))) if voice_on else max(0.1, self.glow_v-dt*2)

        for p in self.cloud:
            p['x'] = p['bx'] + math.sin(self.t*p['sp']+p['ph'])*2.2
            p['y'] = p['by'] + math.cos(self.t*p['sp']*.7+p['ph'])*1.8
            p['ca'] = int(p['ba']*(0.88+0.12*math.sin(self.t*p['sp']*1.4+p['ph'])))

    def draw_cloud(self):
        s = self.screen
        for p in self.cloud:
            x,y,sz,col,a = int(p['x']),int(p['y']),p['sz'],p['col'],p['ca']
            if p['sq'] and sz>=4:
                su = pygame.Surface((sz,sz),pygame.SRCALPHA); su.fill((*col,a))
                s.blit(su,(x-sz//2,y-sz//2))
            else:
                su = pygame.Surface((sz*4,sz*4),pygame.SRCALPHA)
                pygame.draw.circle(su,(*col,a),(sz*2,sz*2),sz)
                s.blit(su,(x-sz*2,y-sz*2))

    # ── flat/SVG helpers ─────────────────────────────────────────────
    @staticmethod
    def _frect(surf, rect, fill, border=None, br=8):
        """Flat filled rect with optional 1-px border."""
        pygame.draw.rect(surf, fill, rect, border_radius=br)
        if border:
            pygame.draw.rect(surf, border, rect, 1, border_radius=br)

    @staticmethod
    def _fpoly(surf, pts, fill, border=None):
        """Flat filled polygon with optional 1-px border."""
        pygame.draw.polygon(surf, fill, pts)
        if border:
            pygame.draw.polygon(surf, border, pts, 1)

    @staticmethod
    def _shine(surf, x, y, w, h):
        """Subtle top-edge white glint on a rounded block."""
        sh = pygame.Surface((w, 3), pygame.SRCALPHA)
        for i in range(w):
            a = int(45 * math.sin(i / max(w-1,1) * math.pi))
            pygame.draw.line(sh, (255,255,255,a), (i,0),(i,2))
        surf.blit(sh, (x, y+4))

    def draw(self):
        # ── Flat SVG-style colours ───────────────────────────────────
        C_HEAD   = (72,  80, 200)   # flat head fill
        C_HEAD_B = (110, 122, 245)  # head border
        C_EAR    = (52,  62, 178)   # ear fill
        C_EAR_B  = (88, 102, 215)   # ear border
        C_NECK   = (60,  70, 188)   # neck
        C_SHLDR  = (52,  66, 182)   # shoulder slab fill
        C_SHLDR_B= (90, 106, 218)   # shoulder border
        C_COLLAR = (80,  92, 205)   # V-collar
        C_VISOR  = (242, 246, 255)  # visor white
        C_EYE_L  = (78, 114, 222)   # left eye
        C_EYE_R  = (68,  52, 190)   # right eye
        C_MOUTH  = (55,  68, 180)   # mouth
        C_WIRE_L = AL;  C_WIRE_R = AR

        s = self.screen
        cx = self.cx;  cy = int(self.cy + self.float_y)
        HW, HH = self.HW, self.HH
        expr = self.expr

        # ── Shoulders ────────────────────────────────────────────────
        sht = cy+HH+20;  shb = cy+HH+42;  sw = 112
        lpts = [(cx-14,sht),(cx-sw,sht),(cx-sw+8,shb),(cx-28,shb)]
        rpts = [(cx+14,sht),(cx+sw,sht),(cx+sw-8,shb),(cx+28,shb)]
        self._fpoly(s, lpts, C_SHLDR, C_SHLDR_B)
        self._fpoly(s, rpts, C_SHLDR, C_SHLDR_B)

        # V-collar
        collar = [(cx-38,sht),(cx+38,sht),(cx+22,sht+18),(cx,sht+30),(cx-22,sht+18)]
        self._fpoly(s, collar, C_COLLAR, lerp3(C_COLLAR,WHITE,0.3))

        # ── Neck ─────────────────────────────────────────────────────
        nr = pygame.Rect(cx-26, cy+HH, 52, 20)
        self._frect(s, nr, C_NECK, br=3)
        for i in range(2):
            pygame.draw.line(s,(30,36,100),(cx-18,cy+HH+5+i*7),(cx+18,cy+HH+5+i*7),1)

        # ── Ears ─────────────────────────────────────────────────────
        for sgn in (-1, 1):
            er = (pygame.Rect(cx-HW-self.EW+6, cy-self.EH//2, self.EW, self.EH)
                  if sgn==-1 else
                  pygame.Rect(cx+HW-6, cy-self.EH//2, self.EW, self.EH))
            self._frect(s, er, C_EAR, C_EAR_B, br=self.ER_)
            self._shine(s, er.x, er.y, er.w, er.h)

        # ── Head ─────────────────────────────────────────────────────
        hr = pygame.Rect(cx-HW, cy-HH, HW*2, HH*2)
        self._frect(s, hr, C_HEAD, C_HEAD_B, br=self.HR_)
        # diagonal corner shine
        shin = pygame.Surface((HW*2, HH*2), pygame.SRCALPHA)
        pts3 = [(0,0),(HW*2,0),(HW*2,int(HH*0.38)),(int(HW*0.65),0)]
        pygame.draw.polygon(shin,(255,255,255,18),pts3)
        s.blit(shin,(cx-HW, cy-HH))
        self._shine(s, cx-HW, cy-HH, HW*2, HH*2)

        # ── Visor ────────────────────────────────────────────────────
        vx = cx - self.VW//2;  vy = cy + self.EYEYR - self.VH//2
        vr = pygame.Rect(vx, vy, self.VW, self.VH)
        pygame.draw.rect(s, C_VISOR, vr, border_radius=self.VR)
        # thin inner shadow at bottom of visor
        pygame.draw.line(s, lerp3(C_VISOR,(180,185,220),.5),
                         (vx+self.VR, vy+self.VH-4),(vx+self.VW-self.VR, vy+self.VH-4), 1)

        # ── Eyes + expressions ───────────────────────────────────────
        ey = cy + self.EYEYR;  h = self.EYEW//2;  off = self.EYEGAP + h

        if self.blinking:
            for ex in [cx-off, cx+off]:
                pygame.draw.line(s, lerp3(C_EYE_L,C_EYE_R,.5),(ex-h,ey),(ex+h,ey),3)

        elif expr == self.EXPR_HAPPY:
            for ex, col in [(cx-off,C_EYE_L),(cx+off,C_EYE_R)]:
                er2 = pygame.Rect(ex-h, ey-h, self.EYEW, self.EYEW)
                pygame.draw.rect(s, col, er2, border_radius=5)
                # squint mask (covers top half)
                pygame.draw.rect(s, C_VISOR,
                                 pygame.Rect(ex-h-1, ey-h-2, self.EYEW+2, h+2))
                # lower highlight
                pygame.draw.rect(s, lerp3(col,WHITE,.45),
                                 pygame.Rect(er2.x+3, ey+2, 9, 6), border_radius=2)

        elif expr == self.EXPR_LISTENING:
            ey_off = int(-4*abs(math.sin(self.t*1.5)))
            for ex, col in [(cx-off,C_EYE_L),(cx+off,C_EYE_R)]:
                er2 = pygame.Rect(ex-h, ey-h+ey_off, self.EYEW, self.EYEW)
                self._frect(s, er2, col, br=5)
                pygame.draw.rect(s, lerp3(col,WHITE,.45),
                                 pygame.Rect(er2.x+4,er2.y+4,8,8), border_radius=2)
            for ex in [cx-off, cx+off]:
                pygame.draw.line(s, lerp3(C_EYE_L,C_EYE_R,.5),
                                 (ex-h+2, ey-h+ey_off-7),(ex+h-2, ey-h+ey_off-10), 2)

        else:  # IDLE / SPEAKING
            for ex, col in [(cx-off,C_EYE_L),(cx+off,C_EYE_R)]:
                er2 = pygame.Rect(ex-h, ey-h, self.EYEW, self.EYEW)
                self._frect(s, er2, col, br=5)
                pygame.draw.rect(s, lerp3(col,WHITE,.45),
                                 pygame.Rect(er2.x+4,er2.y+4,8,8), border_radius=2)
                if self.speaking:
                    pa = int(128+127*abs(math.sin(self.t*10)))
                    bs2 = pygame.Surface((self.EYEW+4,self.EYEW+4),pygame.SRCALPHA)
                    pygame.draw.rect(bs2,(*WHITE,pa),(0,0,self.EYEW+4,self.EYEW+4),2,border_radius=6)
                    s.blit(bs2,(er2.x-2,er2.y-2))

        # ── Mouth ────────────────────────────────────────────────────
        mcy = vy + self.VH + 14
        mc  = C_MOUTH
        if self.mouth_open > 0.08:
            mw = int(30*(.4+self.mouth_open*.6));  mh = int(5+self.mouth_open*12)
            mr = pygame.Rect(cx-mw//2, mcy, mw, mh)
            pygame.draw.ellipse(s, mc, mr)
            if self.mouth_open > .45:
                for i in range(3):
                    pygame.draw.rect(s, C_VISOR,
                                     (cx-mw//2+4+i*(mw//3),mcy+1,mw//3-3,3), border_radius=1)
        elif expr == self.EXPR_HAPPY:
            pygame.draw.arc(s, mc, pygame.Rect(cx-20,mcy-5,40,16), math.pi,math.tau, 3)
        elif expr == self.EXPR_LISTENING:
            pygame.draw.circle(s, mc, (cx, mcy+5), 6)
        else:
            pygame.draw.arc(s, mc, pygame.Rect(cx-14,mcy-2,28,9), math.pi,math.tau, 2)

        # ── Antennas ─────────────────────────────────────────────────
        for base, tip, col in [(self.ANT_LB,self.ANT_LT,C_WIRE_L),
                               (self.ANT_RB,self.ANT_RT,C_WIRE_R)]:
            bx, by = cx+base[0], cy+base[1]
            tx, ty = cx+tip[0],  cy+tip[1]
            pygame.draw.line(s, col, (bx,by),(tx,ty), 2)   # thinner wire
            glow_c(s, tx, ty, 7, col, self.glow_v)          # tip glow
            glow_c(s, bx, by, 4, col, self.glow_v*.5)       # base dot




# ═══════════════════════════════════════════════════════════════════
#  Ollama client  –  streaming mode for low-latency responses
# ═══════════════════════════════════════════════════════════════════
class OllamaClient:
    BASE  = "http://localhost:11434"
    MODEL = "llama3.2:1b"
    RETRY = 3
    # Tokens that mark a sentence boundary worth sending to TTS
    SENT_ENDS = frozenset('.!?\n')

    def __init__(self):
        self.busy       = False
        self._chat_cb   = None   # called once with full text (for chat panel)
        self._speak_cb  = None   # called per sentence (for TTS)
        self.status     = "UNKNOWN"
        self.thinking   = False
        threading.Thread(target=self._check, daemon=True).start()

    def _check(self):
        for _ in range(self.RETRY):
            try:
                r = requests.get(f"{self.BASE}/api/tags", timeout=5)
                if r.status_code == 200:
                    self.status = "OK"
                    print(f"[Ollama] Connected – {self.MODEL}")
                    return
            except Exception:
                pass
            time.sleep(1)
        self.status = "OFFLINE"
        print("[Ollama] Offline – run: ollama serve")

    def set_callback(self, cb):        self._chat_cb  = cb
    def set_speak_callback(self, cb):  self._speak_cb = cb

    def send(self, text):
        if self.busy:
            return
        self.busy     = True
        self.thinking = True
        threading.Thread(target=self._process, args=(text,), daemon=True).start()

    @staticmethod
    def _flush(buf, speak_cb):
        """Send every complete sentence in buf to speak_cb; return remainder."""
        while True:
            best = -1
            for ch in '.!?\n':
                idx = buf.find(ch)
                if idx != -1 and (best == -1 or idx < best):
                    best = idx
            if best < 5:          # too short to be a real sentence
                break
            sentence = buf[:best+1].strip()
            if sentence and speak_cb:
                speak_cb(sentence)
            buf = buf[best+1:].lstrip()
        return buf

    def _process(self, text):
        prompt = (
            "You are a concise, friendly ML Club AI assistant. "
            "Answer in 1-3 short sentences. User: " + text
        )
        for _ in range(self.RETRY):
            try:
                resp = requests.post(
                    f"{self.BASE}/api/generate",
                    json={
                        "model":       self.MODEL,
                        "prompt":      prompt,
                        "stream":      True,
                        "options": {
                            "num_predict": 180,   # cap length for speed
                            "temperature": 0.7,
                            "top_k":       20,
                            "top_p":       0.9,
                        },
                    },
                    timeout=45,
                    stream=True,
                )
                if resp.status_code == 200:
                    self.status   = "OK"
                    full_text     = ""
                    buf           = ""
                    first_token   = True

                    for raw_line in resp.iter_lines():
                        if not raw_line:
                            continue
                        try:
                            chunk = json.loads(raw_line)
                        except Exception:
                            continue

                        token = chunk.get("response", "")
                        if token:
                            if first_token:
                                self.thinking = False  # stop typing dots
                                first_token   = False
                            full_text += token
                            buf       += token
                            buf = self._flush(buf, self._speak_cb)

                        if chunk.get("done", False):
                            break

                    # Speak any trailing fragment
                    if buf.strip() and self._speak_cb:
                        self._speak_cb(buf.strip())

                    # Deliver full text to chat panel
                    if self._chat_cb:
                        self._chat_cb(full_text.strip())

                    self.busy = self.thinking = False
                    return

            except requests.exceptions.ConnectionError:
                self.status = "OFFLINE"
                time.sleep(1.0)
            except requests.exceptions.Timeout:
                time.sleep(0.5)
            except Exception as e:
                print(f"[Ollama] {e}")
                break

        msg = ("Ollama offline – please run `ollama serve`."
               if self.status == "OFFLINE" else "Sorry, I had trouble responding.")
        if self._chat_cb:  self._chat_cb(msg)
        if self._speak_cb: self._speak_cb(msg)
        self.busy = self.thinking = False


# ═══════════════════════════════════════════════════════════════════
#  Script Player  –  3-act ceremony flow
# ═══════════════════════════════════════════════════════════════════
class ScriptPlayer:
    """
    Three-act ceremony script.
    SPACE starts each act; acts play line-by-line waiting for TTS to finish.
    """
    ACTS = [
        # ── Act 1: Opening speech ───────────────────────────────
        [
            "Namaskara Yellarigu!",
            "Good afternoon everyone!",
            "Hope everyone had lunch?",
            "I had mine too… although mine was only charging and software updates.",
            "Ha ha ha!",
            "So… are you all excited for the poster reveal of the ML Club?",
            "I definitely am!",
        ],
        # ── Act 2: Invitation for dignitaries to come on stage ──────
        [
            "Now I request the respected Principal, Dr. Dattatreya sir,"
            " Vice Principal, Dr. K. S. Anand sir,"
            " our honoured guest, and all the HODs to come on the dais.",
        ],
        # ── Act 3: Request dignitaries to say reveal ──────────────
        [
            "I request all the dignitaries to say… reveal the poster.",
        ],
        # ── Act 4: Dramatic countdown ────────────────────────────
        [
            "Get ready, to see the magic…",
            "3…",
            "2…",
            "1…",
            "Here comes the official poster reveal of the ML Club!",
        ],
    ]

    def __init__(self):
        self.running      = False
        self._cb          = None   # line callback(text)
        self._is_speaking = None   # callable → bool
        self._done        = True
        self.current_act  = -1

    def set_callback(self, cb):         self._cb = cb
    def set_speaking_check(self, fn):   self._is_speaking = fn

    def play_act(self, act_num):
        """Start playing act_num (0-indexed). Returns False if already running."""
        if self.running or act_num >= len(self.ACTS):
            return False
        self.current_act = act_num
        self.running     = True
        self._done       = False
        threading.Thread(target=self._run, args=(act_num,), daemon=True).start()
        return True

    def _run(self, act_num):
        lines = self.ACTS[act_num]
        for line in lines:
            if not self.running:
                break
            if self._cb:
                self._cb(line)
            time.sleep(0.5)   # let TTS start
            if self._is_speaking:
                while self._is_speaking():
                    if not self.running:
                        break
                    time.sleep(0.1)
            time.sleep(0.4)   # breath between lines
        self.running = False
        self._done   = True

    def is_complete(self):
        return self._done and not self.running

    def stop(self):
        self.running = False



# ═══════════════════════════════════════════════════════════════════
#  Layout  (recalculated on fullscreen toggle)
# ═══════════════════════════════════════════════════════════════════
def make_layout(W, H):
    M = 12
    LP = int(W * 0.42)
    left  = pygame.Rect(M, M, LP - M*2, H - M*2)
    right = pygame.Rect(LP, M, W - LP - M, H - M*2)
    bcx   = left.centerx
    bcy   = left.centery + 25
    wave  = pygame.Rect(left.x+10, left.bottom-54, left.w-20, 44)
    return left, right, bcx, bcy, wave


# ═══════════════════════════════════════════════════════════════════
#  Draw backgrounds
# ═══════════════════════════════════════════════════════════════════
def draw_bg(screen, W, H):
    for i in range(H):
        t = i/H
        c = lerp3((8,10,22),(12,15,32),t)
        pygame.draw.line(screen,c,(0,i),(W,i))
    gs = 28                           # tighter grid
    for x in range(0,W,gs):
        a=int(10*(1-abs(x-W/2)/(W/2+1)))
        pygame.draw.line(screen,(*((18,22,40)),a),(x,0),(x,H))
    for y in range(0,H,gs):
        a=int(10*(1-abs(y-H/2)/(H/2+1)))
        pygame.draw.line(screen,(*((18,22,40)),a),(0,y),(W,y))



# ═══════════════════════════════════════════════════════════════════
#  HUD
# ═══════════════════════════════════════════════════════════════════
def draw_hud(screen, state, voice_on, ol_status, fonts):
    fM,fS,fXS = fonts
    W = screen.get_width()

    # Ollama badge top-right (only in chat mode, others don't need it prominently)
    bc  = {"OK":GREEN,"OFFLINE":RED}.get(ol_status,ORANGE)
    bl  = {"OK":"● Online","OFFLINE":"● Offline"}.get(ol_status,"● Connecting")
    bs  = fXS.render(f"Ollama {bl}",True,bc)
    bx  = W - bs.get_width() - 24
    br  = pygame.Rect(bx-8,12,bs.get_width()+16,26)
    glass_panel(screen,br,bc,radius=12,bga=20,ba=90)
    screen.blit(bs,(bx,18))

    # State badge top-left  —  friendly human-readable labels, no tech words
    STATE_LABEL = {
        IDLE:   ("⏸",   "Ready",          MUTED),
        ACT1:   ("🎙",   "Opening",         BLUE),
        ACT2:   ("👥",   "Invitation",      PURP),
        ACT3:   ("🎤",   "Request",         ORANGE),
        ACT4:   ("⏳",   "Countdown",       RED),
        POSTER: ("🎨",   "Poster Reveal",   PURP),
        CHAT:   ("💬",   "AI Chat",         GREEN),
    }
    icon, label, sc = STATE_LABEL.get(state, (".",state,WHITE))
    stxt = fS.render(f"{icon}  {label}", True, sc)
    sr   = pygame.Rect(12,12,stxt.get_width()+24,28)
    glass_panel(screen,sr,sc,radius=12,bga=20,ba=90)
    screen.blit(stxt,(24,18))

    # Hint line below state badge
    HINTS = {
        IDLE:   "Press SPACE to start",
        ACT1:   "SPACE → next when done",
        ACT2:   "SPACE → next when done",
        ACT3:   "SPACE → next when done",
        ACT4:   "P → reveal the poster!",
        POSTER: "C → enter AI chat",
        CHAT:   "🎤 VOICE ON" if voice_on else "🔇 VOICE OFF",
    }
    hint_col = GREEN if (state==CHAT and voice_on) else MUTED
    hi = fXS.render(HINTS.get(state,""), True, hint_col)
    hr2 = pygame.Rect(12,44,hi.get_width()+24,22)
    glass_panel(screen,hr2,hint_col,radius=10,bga=12,ba=65)
    screen.blit(hi,(24,50))


# ═══════════════════════════════════════════════════════════════════
#  Poster screen
# ═══════════════════════════════════════════════════════════════════
def draw_poster(screen, t, confetti=None, flash_t=0.0):
    W,H = screen.get_size()
    # Background
    for i in range(H):
        p=i/H; pygame.draw.line(screen,lerp3((12,15,40),(60,50,120),p),(0,i),(W,i))

    # Animated glow burst behind the text (expands from center)
    burst_r = min(int(flash_t * 400), int(min(W,H)*0.6))
    if burst_r > 0:
        gv = abs(math.sin(t*2.2))
        gc = lerp3(BLUE, PURP, gv)
        for ring in range(4):
            ra = max(0, int(60*(1 - ring/4) * max(0, 1-flash_t*0.4)))
            if ra > 0:
                s = pygame.Surface((burst_r*2, burst_r*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*gc, ra), (burst_r, burst_r), burst_r - ring*20)
                screen.blit(s, (W//2 - burst_r, H//2 - burst_r))

    gv = abs(math.sin(t*2.2))
    gc = lerp3(BLUE,PURP,gv)
    # Text with scale-in effect for first second
    scale = min(1.0, flash_t * 1.8)
    for txt,col,sz,y in [
        ("🤖  ML Club AI Bot",gc, 80, H//2-130),
        ("Powered by Ollama + Local LLM",WHITE,52,H//2-40),
        ("✨ Voice · TTS · Smart Responses",GREEN,40,H//2+60),
        ("Welcome to the ML Club!",PURP,38,H//2+140),
    ]:
        eff_sz = max(8, int(sz * scale))
        f=pygame.font.Font(None,eff_sz); surf=f.render(txt,True,col)
        screen.blit(surf,surf.get_rect(center=(W//2,y)))

    # Confetti shower
    if confetti:
        confetti.draw(screen)

    # White flash overlay (fades in first 0.5s)
    flash_a = max(0, int(255 * (1 - flash_t * 2.0)))
    if flash_a > 0:
        fl = pygame.Surface((W, H), pygame.SRCALPHA)
        fl.fill((255, 255, 255, flash_a))
        screen.blit(fl, (0, 0))



# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════
def main():
    pygame.init()
    info     = pygame.display.Info()
    FULL_W, FULL_H = info.current_w, info.current_h
    is_fs    = False
    W, H     = WIN_W, WIN_H
    screen   = pygame.display.set_mode((W,H), pygame.RESIZABLE)
    pygame.display.set_caption("🤖 ML Club AI Bot")
    clock    = pygame.time.Clock()

    # Fonts — JetBrains Mono loaded from project directory
    fL  = jbmono(22, bold=True)
    fM  = jbmono(18)
    fS  = jbmono(15)
    fXS = jbmono(13)
    fonts_hud = (fM, fS, fXS)

    # Build layout
    left, right, bcx, bcy, wave_rect = make_layout(W, H)

    # Systems
    aurora   = Aurora(W, H)
    neural   = FloatDots(W, H)   # dark blurred drifting circles
    orbits   = Orbits()
    pulses   = Pulses()
    scanline = ScanLine()
    waveform = Waveform(wave_rect)
    chat     = ChatPanel(right)
    bot      = MLClubBot(screen, bcx, bcy)
    audio    = AudioSystem()
    voice    = RobustVoiceInput()
    ollama   = OllamaClient()
    script   = ScriptPlayer()

    state        = IDLE
    voice_on     = False
    gt           = 0.0
    last_emit    = 0.0
    confetti     = Confetti(W, H)
    poster_flash = 0.0

    # Callbacks
    def on_script_line(text):
        """Each ceremony line — show in chat + speak."""
        chat.add("bot", text)
        audio.speak_text(text)
    def on_voice(text):
        chat.add("user", text)
        ollama.send(text)
    def on_ai_sentence(sentence):
        audio.speak_text(sentence)
    def on_ai_complete(full_reply):
        chat.add("bot", full_reply)

    script.set_callback(on_script_line)
    script.set_speaking_check(audio.is_speaking)
    voice.set_voice_callback(on_voice)
    ollama.set_callback(on_ai_complete)
    ollama.set_speak_callback(on_ai_sentence)
    print("[System] ML Club Bot ready – SPACE to begin.")

    def rebuild(new_w, new_h):
        nonlocal left, right, bcx, bcy, wave_rect, waveform, chat, bot, aurora, neural, confetti
        left, right, bcx, bcy, wave_rect = make_layout(new_w, new_h)
        waveform = Waveform(wave_rect)
        chat.rect = right
        bot.cx = bcx; bot.cy = bcy
        bot.cloud = _build_cloud(bcx, bcy)
        aurora = Aurora(new_w, new_h)
        neural = NeuralBG(new_w, new_h)
        confetti = Confetti(new_w, new_h)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        gt += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                k = event.key
                if k == pygame.K_ESCAPE:
                    if is_fs:
                        is_fs = False; W,H = WIN_W,WIN_H
                        screen = pygame.display.set_mode((W,H), pygame.RESIZABLE)
                        rebuild(W,H)
                    else:
                        running = False
                elif k == pygame.K_f:
                    is_fs = not is_fs
                    if is_fs:
                        W,H = FULL_W,FULL_H
                        screen = pygame.display.set_mode((W,H), pygame.FULLSCREEN)
                    else:
                        W,H = WIN_W,WIN_H
                        screen = pygame.display.set_mode((W,H), pygame.RESIZABLE)
                    rebuild(W,H); bot.screen = screen
                elif k == pygame.K_SPACE:
                    # SPACE steps through the 4 ceremony acts
                    if state == IDLE:
                        state = ACT1;  script.play_act(0)
                    elif state == ACT1 and script.is_complete():
                        state = ACT2;  script.play_act(1)
                    elif state == ACT2 and script.is_complete():
                        state = ACT3;  script.play_act(2)
                    elif state == ACT3 and script.is_complete():
                        state = ACT4;  script.play_act(3)
                    # ACT4 → POSTER is P only (dramatic moment!)
                elif k == pygame.K_v and state == CHAT:
                    voice_on = not voice_on
                    if voice_on: voice.start_listening(); pulses.emit(bcx,bcy,CYAN)
                    else:        voice.stop_listening();  pulses.emit(bcx,bcy,MUTED)
                elif k == pygame.K_p and state == ACT4 and script.is_complete():
                    state = POSTER
                    poster_flash = 0.0
                    confetti.burst()
                elif k == pygame.K_c and state == POSTER:
                    state = CHAT
                elif k == pygame.K_r:
                    state=IDLE; voice_on=False
                    voice.stop_listening(); script.stop()
            elif event.type == pygame.VIDEORESIZE and not is_fs:
                W,H = event.w, event.h
                screen = pygame.display.set_mode((W,H), pygame.RESIZABLE)
                rebuild(W,H); bot.screen = screen

        # No auto-transitions — SPACE / P / C drive the flow

        speaking = audio.is_speaking()

        # Emit speaking pulses periodically
        if speaking and gt - last_emit > 0.55:
            pulses.emit(bcx, int(bcy + bot.float_y), lerp3(BLUE,PURP,abs(math.sin(gt*1.2))))
            last_emit = gt

        # Update all systems
        bot.update(dt, voice_on, speaking, state)
        aurora.update(dt, gt)
        neural.update(dt)
        orbits.update(dt)
        pulses.update(dt)
        scanline.update(dt, bcy - 85, bcy + 85)
        waveform.update(dt, voice_on or speaking, gt)
        chat.update(dt, ollama.thinking)
        if state == POSTER:
            confetti.update(dt)
            poster_flash += dt

        # ── DRAW ────────────────────────────────────────────────────
        screen.fill(BG)
        draw_bg(screen, W, H)
        aurora.draw(screen)

        # Neural network (only in background area – both panels)
        neural.draw(screen)

        # Left panel glass
        glass_panel(screen, left, BLUE, radius=20, bga=18, ba=80)

        # Orbit rings (behind bot)
        orbits.draw(screen, bcx, int(bcy+bot.float_y), bot.glow_v)

        # Pulse rings
        pulses.draw(screen)

        # Pixel cloud
        bot.draw_cloud()

        # Bot character
        bot.draw()

        # Scan line over bot
        scanline.draw(screen, left.x+8, left.right-8)

        # Bot panel label
        lbl = fXS.render("ML CLUB AI BOT", True, (*MUTED, 200))
        screen.blit(lbl, (left.centerx - lbl.get_width()//2, left.y + 8))

        # Waveform
        glass_panel(screen, wave_rect, CYAN if (voice_on or speaking) else MUTED,
                    radius=10, bga=15, ba=70)
        waveform.draw(screen, voice_on or speaking)

        # State hints in bot panel
        ACT_STATES = (ACT1, ACT2, ACT3, ACT4)
        if state == IDLE:
            hint = fS.render("Press SPACE to begin", True, MUTED)
            screen.blit(hint, (left.centerx - hint.get_width()//2, left.bottom - wave_rect.h - 30))
        elif state in ACT_STATES and not script.is_complete():
            dot  = int(gt * 3) % 4
            hint = fS.render("Speaking" + "." * dot, True, lerp3(MUTED, CYAN, abs(math.sin(gt*2))))
            screen.blit(hint, (left.centerx - hint.get_width()//2, left.bottom - wave_rect.h - 30))
        elif state in (ACT1, ACT2, ACT3) and script.is_complete():
            hint = fS.render("Press SPACE for next", True, lerp3(MUTED, GREEN, abs(math.sin(gt*2))))
            screen.blit(hint, (left.centerx - hint.get_width()//2, left.bottom - wave_rect.h - 30))
        elif state == ACT4 and script.is_complete():
            pulse = abs(math.sin(gt * 3))
            hint = fS.render("🎨 Press P to reveal!", True, lerp3(ORANGE, WHITE, pulse))
            screen.blit(hint, (left.centerx - hint.get_width()//2, left.bottom - wave_rect.h - 30))

        # Right panel: chat or POSTER
        if state == POSTER:
            draw_poster(screen, gt, confetti, poster_flash)
        else:
            chat.draw(screen)

        # HUD overlays
        draw_hud(screen, state, voice_on, ollama.status, fonts_hud)

        pygame.display.flip()

    voice.stop_listening()
    audio.stop()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
