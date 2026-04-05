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
BG    = (4,   5,  12);   BG2   = (6,   8,  18)
BLUE  = (74,  158, 255); PURP  = (180,  78, 255)
CYAN  = (45,  210, 255); GREEN = (80,  220, 140)
ORANGE= (255, 165,  60); RED   = (255,  80,  80)
WHITE = (248, 250, 255); MUTED = (70,   80, 125)

# Fixed 16:9 aspect ratio
ASPECT_RATIO = WIN_W / WIN_H   # 1280/720 = 16:9

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
#  Scale factor — everything sizes relative to this
# ═══════════════════════════════════════════════════════════════════
def get_scale(W, H):
    """Return a scale factor relative to the base 1280×720 design."""
    return min(W / WIN_W, H / WIN_H)


# ═══════════════════════════════════════════════════════════════════
#  Pixel cloud builder
# ═══════════════════════════════════════════════════════════════════
def _build_cloud(cx, cy, sf=1.0):
    """Pixel cloud that scales with the window."""
    SC = 0.70 * sf
    rng = random.Random(2024)
    items = []
    ox, oy = cx + int(95*SC), cy - int(85*SC)
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
            items.append({'bx':ox+int(dx*SC)+rng.uniform(-2,2),
                          'by':oy+int(dy*SC)+rng.uniform(-2,2),
                          'x':0,'y':0,'sz':max(1,int(sz*SC)),'sq':True,
                          'col':CLOUD_COL[ci],'ba':232,
                          'ph':rng.uniform(0,6.28),'sp':rng.uniform(.2,.7),'ca':232})
    for _ in range(65):
        dx = rng.uniform(-30,-170)*sf; dy = rng.uniform(-30,-120)*sf
        dist = math.sqrt(dx*dx+dy*dy); norm = min(dist/(150*sf),1.0)
        sz = max(1,int((1-norm)*6*sf+1)); sq = sz>=4; ci = min(int(norm*6)+3,8)
        items.append({'bx':ox+int(dx),'by':oy+int(dy),'x':0,'y':0,'sz':sz,'sq':sq,
                      'col':CLOUD_COL[ci],'ba':max(60,int(180*(1-norm*.55))),
                      'ph':rng.uniform(0,6.28),'sp':rng.uniform(.1,.5),'ca':100})
    return items


# ═══════════════════════════════════════════════════════════════════
#  Bot renderer — all dimensions scale with sf
# ═══════════════════════════════════════════════════════════════════
class MLClubBot:
    # Base dimensions at 1280×720 (scale factor = 1.0)
    _BASE_HW, _BASE_HH = 66, 59
    _BASE_HR  = 10
    _BASE_EW, _BASE_EH, _BASE_ER = 17, 64, 6
    _BASE_VW, _BASE_VH, _BASE_VR = 106, 48, 20
    _BASE_EYEW, _BASE_EYEGAP, _BASE_EYEYR = 25, 20, -7
    _BASE_ANT_LB = (-75, -27)
    _BASE_ANT_LT = (-116, -77)
    _BASE_ANT_RB = ( 75, -28)
    _BASE_ANT_RT = ( 104, -76)

    # Expression states
    EXPR_IDLE     = 0
    EXPR_HAPPY    = 1
    EXPR_THINKING = 2
    EXPR_LISTENING= 3

    def __init__(self, screen, cx, cy, sf=1.0):
        self.screen = screen
        self.cx, self.cy = cx, cy
        self.sf = sf
        self._apply_scale(sf)
        self.t = 0.0; self.float_y = 0.0
        self.blink_t = 0.0; self.blinking = False
        self.mouth_open = 0.0; self.speaking = False
        self.glow_v = 0.1
        self.expr = self.EXPR_IDLE
        self.expr_t = 0.0
        self.think_wave = 0.0
        self.cloud = _build_cloud(cx, cy, sf)

    def _apply_scale(self, sf):
        """Recompute all pixel dimensions from the base values."""
        self.sf = sf
        s = sf
        self.HW  = int(self._BASE_HW * s)
        self.HH  = int(self._BASE_HH * s)
        self.HR_ = max(2, int(self._BASE_HR * s))
        self.EW  = max(2, int(self._BASE_EW * s))
        self.EH  = max(4, int(self._BASE_EH * s))
        self.ER_ = max(1, int(self._BASE_ER * s))
        self.VW  = max(8, int(self._BASE_VW * s))
        self.VH  = max(6, int(self._BASE_VH * s))
        self.VR  = max(4, int(self._BASE_VR * s))
        self.EYEW    = max(4, int(self._BASE_EYEW * s))
        self.EYEGAP  = max(2, int(self._BASE_EYEGAP * s))
        self.EYEYR   = int(self._BASE_EYEYR * s)
        self.ANT_LB  = (int(self._BASE_ANT_LB[0]*s), int(self._BASE_ANT_LB[1]*s))
        self.ANT_LT  = (int(self._BASE_ANT_LT[0]*s), int(self._BASE_ANT_LT[1]*s))
        self.ANT_RB  = (int(self._BASE_ANT_RB[0]*s), int(self._BASE_ANT_RB[1]*s))
        self.ANT_RT  = (int(self._BASE_ANT_RT[0]*s), int(self._BASE_ANT_RT[1]*s))

    def update(self, dt, voice_on, speaking, state=None):
        self.t += dt; self.speaking = speaking
        self.float_y = (math.sin(self.t*1.4)*7 + math.sin(self.t*2.8)*2.5) * self.sf
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
    def _frect(surf, rect, fill, border=None, br=12):
        """Flat filled rect with smooth rounded corners, optional 1-px border."""
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
        sc = self.sf

        # ── Shoulders (scaled) ──────────────────────────────────────────────
        sht = cy+HH+int(14*sc);  shb = cy+HH+int(30*sc);  sw = int(78*sc)
        lpts = [(cx-int(10*sc),sht),(cx-sw,sht),(cx-sw+int(6*sc),shb),(cx-int(20*sc),shb)]
        rpts = [(cx+int(10*sc),sht),(cx+sw,sht),(cx+sw-int(6*sc),shb),(cx+int(20*sc),shb)]
        self._fpoly(s, lpts, C_SHLDR, C_SHLDR_B)
        self._fpoly(s, rpts, C_SHLDR, C_SHLDR_B)

        # V-collar
        c27=int(27*sc); c15=int(15*sc); c13=int(13*sc); c21=int(21*sc)
        collar = [(cx-c27,sht),(cx+c27,sht),(cx+c15,sht+c13),(cx,sht+c21),(cx-c15,sht+c13)]
        self._fpoly(s, collar, C_COLLAR, lerp3(C_COLLAR,WHITE,0.3))

        # ── Neck (scaled) ─────────────────────────────────────────────────
        nw2=int(18*sc); nh=int(14*sc)
        nr = pygame.Rect(cx-nw2, cy+HH, nw2*2, nh)
        self._frect(s, nr, C_NECK, br=max(1,int(3*sc)))
        nlw=int(12*sc)
        for i in range(2):
            pygame.draw.line(s,(30,36,100),(cx-nlw,cy+HH+int(3*sc)+int(i*5*sc)),(cx+nlw,cy+HH+int(3*sc)+int(i*5*sc)),1) # neck

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
            ey_off = int(-4*self.sf*abs(math.sin(self.t*1.5)))
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
            pygame.draw.line(s, col, (bx,by),(tx,ty), max(1,int(2*sc)))   # thinner wire
            glow_c(s, tx, ty, max(2,int(7*sc)), col, self.glow_v)        # tip glow
            glow_c(s, bx, by, max(1,int(4*sc)), col, self.glow_v*.5)     # base dot




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
    sf = get_scale(W, H)
    M = max(6, int(14 * sf))
    LP = int(W * 0.42)
    left  = pygame.Rect(M, M, LP - M*2, H - M*2)
    right = pygame.Rect(LP, M, W - LP - M, H - M*2)
    bcx   = left.centerx
    bcy   = left.centery + int(18 * sf)
    wh    = max(16, int(38 * sf))
    wave  = pygame.Rect(left.x + int(10*sf), left.bottom - wh - int(10*sf), left.w - int(20*sf), wh)
    return left, right, bcx, bcy, wave


# ═══════════════════════════════════════════════════════════════════
#  Draw backgrounds
# ═══════════════════════════════════════════════════════════════════
def draw_bg(screen, W, H):
    """Dark gradient background — clean, no grid lines."""
    for i in range(H):
        t = i/H
        c = lerp3((4,5,12),(6,8,18),t)
        pygame.draw.line(screen,c,(0,i),(W,i))



# (HUD badges removed)



# ═══════════════════════════════════════════════════════════════════
#  Poster screen — JetBrains Mono, minimal modern design
# ═══════════════════════════════════════════════════════════════════
def draw_poster(screen, t, confetti=None, flash_t=0.0):
    W, H = screen.get_size()
    sf = min(W / 1280, H / 720)

    # Dark gradient background
    for i in range(H):
        p = i / H
        pygame.draw.line(screen, lerp3((6, 8, 18), (12, 14, 28), p), (0, i), (W, i))

    # Subtle centre glow (single soft circle)
    glow_r = int(min(W, H) * 0.35)
    if glow_r > 0:
        gv = abs(math.sin(t * 1.2))
        gc = lerp3(BLUE, PURP, gv)
        gs = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*gc, int(18 + 8*gv)), (glow_r, glow_r), glow_r)
        screen.blit(gs, (W//2 - glow_r, H//2 - glow_r))

    # Text with scale-in effect
    scale = min(1.0, flash_t * 1.8)
    lines = [
        ("ML Club AI Bot",    BLUE,   max(10, int(42 * sf * scale)), H//2 - int(80*sf)),
        ("Powered by Ollama + Local LLM", WHITE, max(8, int(22 * sf * scale)), H//2 - int(20*sf)),
        ("──────────",        MUTED,  max(6, int(14 * sf * scale)), H//2 + int(15*sf)),
        ("Voice · TTS · Smart Responses", GREEN, max(7, int(18 * sf * scale)), H//2 + int(50*sf)),
        ("Welcome to the ML Club!",       PURP,  max(7, int(16 * sf * scale)), H//2 + int(90*sf)),
    ]
    for txt, col, sz, y in lines:
        f = jbmono(sz)
        surf = f.render(txt, True, col)
        screen.blit(surf, surf.get_rect(center=(W//2, y)))

    # Confetti
    if confetti:
        confetti.draw(screen)

    # White flash overlay
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

    def clamp_aspect(w, h):
        """Enforce fixed 16:9 aspect ratio."""
        target_h = int(w / ASPECT_RATIO)
        if target_h <= h:
            return w, target_h
        else:
            return int(h * ASPECT_RATIO), h
    pygame.display.set_caption("🤖 ML Club AI Bot")
    clock    = pygame.time.Clock()
    sf       = get_scale(W, H)

    # Fonts — scaled to window size
    def make_fonts(sf):
        return (
            jbmono(max(8, int(20 * sf)), bold=True),   # fL
            jbmono(max(6, int(15 * sf))),               # fM
            jbmono(max(5, int(13 * sf))),               # fS
            jbmono(max(5, int(11 * sf))),               # fXS
        )
    fL, fM, fS, fXS = make_fonts(sf)

    # Build layout
    left, right, bcx, bcy, wave_rect = make_layout(W, H)

    # Systems
    aurora   = Aurora(W, H)
    neural   = FloatDots(W, H)   # pixelated grid shimmer effect
    orbits   = Orbits()
    pulses   = Pulses()
    scanline = ScanLine()
    waveform = Waveform(wave_rect)
    chat     = ChatPanel(right, sf)
    bot      = MLClubBot(screen, bcx, bcy, sf)
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
        nonlocal left, right, bcx, bcy, wave_rect, waveform, bot, aurora, neural, confetti, sf, fL, fM, fS, fXS
        sf = get_scale(new_w, new_h)
        fL, fM, fS, fXS = make_fonts(sf)
        left, right, bcx, bcy, wave_rect = make_layout(new_w, new_h)
        waveform = Waveform(wave_rect)
        # Update chat panel — preserve existing messages
        chat.resize(right, sf)
        bot.cx = bcx; bot.cy = bcy
        bot._apply_scale(sf)
        bot.cloud = _build_cloud(bcx, bcy, sf)
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
                        W,H = clamp_aspect(FULL_W, FULL_H)
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
                W,H = clamp_aspect(event.w, event.h)
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
        scanline.update(dt, bcy - bot.HH, bcy + bot.HH)
        waveform.update(dt, voice_on or speaking, gt)
        chat.update(dt, ollama.thinking)
        if state == POSTER:
            confetti.update(dt)
            poster_flash += dt

        # ── DRAW ────────────────────────────────────────────────────
        screen.fill(BG)
        draw_bg(screen, W, H)

        # Pixelated grid shimmer effect
        neural.draw(screen)

        # Left panel glass
        glass_panel(screen, left, BLUE, radius=max(6,int(20*sf)), bga=18, ba=80)

        # Orbit rings (behind bot)
        orbits.draw(screen, bcx, int(bcy+bot.float_y), bot.glow_v, sf)

        # Pulse rings
        pulses.draw(screen)

        # Pixel cloud
        bot.draw_cloud()

        # Bot character
        bot.draw()

        # White glow sweep over bot
        scanline.draw(screen, left.x+8, left.right-8)

        # Bot panel label
        lbl = fM.render("ML CLUB AI BOT", True, (*MUTED, 200))
        screen.blit(lbl, (left.centerx - lbl.get_width()//2, left.y + max(4,int(10*sf))))

        # Waveform
        glass_panel(screen, wave_rect, CYAN if (voice_on or speaking) else MUTED,
                    radius=max(4,int(10*sf)), bga=15, ba=70)
        waveform.draw(screen, voice_on or speaking)


        # Right panel: chat or POSTER
        if state == POSTER:
            draw_poster(screen, gt, confetti, poster_flash)
        else:
            chat.draw(screen)

        pygame.display.flip()

    voice.stop_listening()
    audio.stop()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
