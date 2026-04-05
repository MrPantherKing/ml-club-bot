# ui_systems.py — Animation subsystems for ML Club Bot
import math, random, pygame

# ── Palette (shared) ─────────────────────────────────────────────
BLUE  = (74,  158, 255)
PURP  = (180,  78, 255)
CYAN  = (45,  210, 255)
GREEN = (80,  220, 140)
WHITE = (255, 255, 255)
MUTED = (70,   80, 125)

# ── Micro-helpers ─────────────────────────────────────────────────
def lerp3(a, b, t):
    return (int(a[0]+(b[0]-a[0])*t), int(a[1]+(b[1]-a[1])*t), int(a[2]+(b[2]-a[2])*t))

def ease_out(t):
    return 1 - (1 - min(t, 1.0)) ** 3

def grad_h(surf, rect, cl, cr, r=0):
    """Horizontal gradient filled rounded-rect on surf."""
    w, h = rect.w, rect.h
    tmp = pygame.Surface((w, h), pygame.SRCALPHA)
    for x in range(w):
        pygame.draw.line(tmp, lerp3(cl, cr, x / max(w-1, 1)), (x, 0), (x, h-1))
    if r:
        m = pygame.Surface((w, h), pygame.SRCALPHA)
        m.fill((0, 0, 0, 0))
        pygame.draw.rect(m, (255,255,255,255), (0,0,w,h), border_radius=r)
        tmp.blit(m, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
    surf.blit(tmp, (rect.x, rect.y))

def glow_c(surf, x, y, r, col, g=1.0):
    """Glowing circle."""
    gr = int(r * 2.5 + g * 6)
    if gr < 2: return
    s = pygame.Surface((gr*2, gr*2), pygame.SRCALPHA)
    pygame.draw.circle(s, (*col, int(90*g)), (gr, gr), gr)
    surf.blit(s, (x-gr, y-gr))
    pygame.draw.circle(surf, col, (x, y), r)
    if r > 3:
        pygame.draw.circle(surf, (255,255,255), (x - r//3, y - r//3), max(1, r//3))

def glass_panel(surf, rect, bcol, radius=16, bga=28, ba=105):
    """Glassmorphism panel: frosted glass + coloured border."""
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (255,255,255,bga), (0,0,rect.w,rect.h), border_radius=radius)
    # top highlight streak
    for x in range(rect.w - 8):
        a = int(48 * math.sin(x / max(rect.w-9, 1) * math.pi))
        pygame.draw.line(s, (255,255,255,a), (x+4, 2), (x+4, 3))
    bo = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(bo, (*bcol, ba), (0,0,rect.w,rect.h), 2, border_radius=radius)
    s.blit(bo, (0,0))
    surf.blit(s, (rect.x, rect.y))

_JBM_PATH  = None   # will be set to TTF file path on first call
_JBM_B_PATH= None

def jbmono(size, bold=False):
    """Load JetBrains Mono from the project folder, or fall back to a system monospace."""
    global _JBM_PATH, _JBM_B_PATH
    import os, pathlib

    # Discover font files relative to this module
    if _JBM_PATH is None:
        here = pathlib.Path(__file__).parent
        for f in ('JetBrainsMono-Regular.ttf', 'JetBrainsMono.ttf'):
            if (here / f).exists():
                _JBM_PATH = str(here / f); break
    if _JBM_B_PATH is None:
        here = pathlib.Path(__file__).parent
        for f in ('JetBrainsMono-Bold.ttf', 'JetBrainsMono-Regular.ttf'):
            if (here / f).exists():
                _JBM_B_PATH = str(here / f); break

    path = (_JBM_B_PATH if bold else _JBM_PATH)
    if path:
        try:
            return pygame.font.Font(path, size)
        except Exception:
            pass
    # System fallback: prefer monospace options
    for n in ("JetBrains Mono","Cascadia Code","Consolas","Courier New","Courier"):
        try:
            return pygame.font.SysFont(n, size, bold=bold)
        except Exception:
            pass
    return pygame.font.Font(None, size)

# backward-compat alias
def sysfont(size, bold=False):
    return jbmono(size, bold)


# ═══════════════════════════════════════════════════════════════
class Aurora:
    """Slow-drifting glow blobs for animated background."""
    def __init__(self, W, H):
        rng = random.Random(77)
        self.W, self.H = W, H
        self.blobs = [
            {'x': rng.uniform(0,W), 'y': rng.uniform(0,H),
             'r': rng.uniform(min(W,H)*.20, min(W,H)*.46),
             'col': rng.choice([BLUE, PURP, CYAN, (55,100,220)]),
             'vx': rng.uniform(-16,16), 'vy': rng.uniform(-13,13),
             'ph': rng.uniform(0,6.28), 'sp': rng.uniform(.12,.38),
             'ba': rng.uniform(7,15)}
            for _ in range(5)]

    def update(self, dt, t):
        for b in self.blobs:
            b['x'] = (b['x'] + b['vx']*dt) % self.W
            b['y'] = (b['y'] + b['vy']*dt) % self.H
            b['ca'] = b['ba'] * (0.7 + 0.3 * math.sin(t * b['sp'] + b['ph']))

    def draw(self, surf):
        for b in self.blobs:
            r = int(b['r']); ca = b.get('ca', b['ba'])
            for i in range(5):
                ri = int(r*(1-i/5)); ai = int(ca*(1-i/5)**2.5)
                if ri > 0 and ai > 0:
                    s = pygame.Surface((ri*2, ri*2), pygame.SRCALPHA)
                    pygame.draw.circle(s, (*b['col'], ai), (ri,ri), ri)
                    surf.blit(s, (int(b['x'])-ri, int(b['y'])-ri))


# ═══════════════════════════════════════════════════════════════
class FloatDots:
    """
    Dark, softly-blurred circles drifting slowly across the background.
    Replaces the constellation/neural-network dots.
    """
    def __init__(self, W, H, n=28):
        rng = random.Random(31)
        self.W, self.H = W, H
        self.nodes = [
            {'x':  rng.uniform(0, W),
             'y':  rng.uniform(0, H),
             'vx': rng.uniform(-6, 6),
             'vy': rng.uniform(-5, 5),
             'r':  rng.uniform(10, 34),
             'a':  rng.uniform(18, 42)}   # base alpha
            for _ in range(n)
        ]

    def update(self, dt):
        for nd in self.nodes:
            nd['x'] = (nd['x'] + nd['vx']*dt) % self.W
            nd['y'] = (nd['y'] + nd['vy']*dt) % self.H

    def draw(self, surf):
        for nd in self.nodes:
            x, y, r = int(nd['x']), int(nd['y']), int(nd['r'])
            a = int(nd['a'])
            # 3-layer soft blur: outer faint, inner darker
            for i in range(3):
                ri = max(1, int(r * (1 - i*0.25)))
                ai = max(0, int(a * (0.5 + i*0.25)))
                sf = pygame.Surface((ri*2, ri*2), pygame.SRCALPHA)
                pygame.draw.circle(sf, (0, 0, 0, ai), (ri, ri), ri)
                surf.blit(sf, (x-ri, y-ri))

# keep the old name as an alias so existing code doesn't break
NeuralBG = FloatDots


# ═══════════════════════════════════════════════════════════════
class Orbits:
    """
    Three tilted elliptical orbits, each with:
    - A fading trail arc behind the planet
    - A larger glowing planet with an inner highlight
    - Slightly different tilt  for a 3-D "solar system" feel
    """
    #          rx   ry   speed  tilt  col   ring_a  planet_r
    _RINGS = [
        (132, 46,  0.40,  0.18, BLUE,  50,  7),
        (160, 58, -0.28, -0.12, PURP,  35,  6),
        ( 96, 30,  0.65,  0.28, CYAN,  70,  5),
    ]
    TRAIL_STEPS = 18   # how many trail segments to draw
    TRAIL_ARC   = 0.55 # radians of trail

    def __init__(self):
        self.angles = [0.0 for _ in self._RINGS]

    def update(self, dt):
        for i, r in enumerate(self._RINGS):
            self.angles[i] += r[2] * dt

    @staticmethod
    def _orbit_pos(cx, cy, rx, ry, tilt, angle):
        """Return screen (x,y) for a point on a tilted ellipse."""
        # Rotate the standard ellipse point by `tilt` radians
        ex = rx * math.cos(angle)
        ey = ry * math.sin(angle)
        x = cx + int(ex * math.cos(tilt) - ey * math.sin(tilt))
        y = cy + int(ex * math.sin(tilt) + ey * math.cos(tilt))
        return x, y

    def draw(self, surf, cx, cy, glow_i=0.2):
        for i, (rx, ry, spd, tilt, col, ring_a, pr) in enumerate(self._RINGS):
            angle = self.angles[i]

            # -- Orbit ellipse (draw as many small line segments) --
            pts = []
            for step in range(60):
                a = step / 60 * math.tau
                pts.append(self._orbit_pos(cx, cy, rx, ry, tilt, a))
            for j in range(len(pts)):
                pygame.draw.line(surf, (*col, ring_a), pts[j], pts[(j+1) % len(pts)], 1)

            # -- Trail: fading arc behind the planet --
            for step in range(self.TRAIL_STEPS):
                frac = step / self.TRAIL_STEPS
                trail_a = angle - frac * self.TRAIL_ARC * (1 if spd > 0 else -1)
                tx, ty = self._orbit_pos(cx, cy, rx, ry, tilt, trail_a)
                trail_alpha = int((1 - frac) * 160 * (0.5 + glow_i * 0.5))
                trail_r = max(1, int(pr * (1 - frac * 0.7)))
                s = pygame.Surface((trail_r*2+2, trail_r*2+2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*col, trail_alpha), (trail_r+1, trail_r+1), trail_r)
                surf.blit(s, (tx - trail_r - 1, ty - trail_r - 1))

            # -- Planet (glowing circle + highlight) --
            px, py = self._orbit_pos(cx, cy, rx, ry, tilt, angle)
            glow_c(surf, px, py, pr, col, 0.6 + glow_i * 0.55)





# ═══════════════════════════════════════════════════════════════
class Confetti:
    """Physics-based confetti shower for the poster reveal."""
    COLORS = [
        (255, 70,  70),  (255, 200,  0),  (70, 220,  70),
        (70, 160, 255),  (255, 100, 255), (255, 145,   0),
        (170, 70, 255),  (0,  230, 220),  (255, 255,  70),
        (255, 255, 255),
    ]

    def __init__(self, W, H):
        self.W, self.H  = W, H
        self.particles  = []
        self.spawn_t    = 999.0
        self._rng       = random.Random()

    def burst(self):
        self.spawn_t = 0.0
        self.particles.clear()
        for _ in range(260):
            self._spawn()

    def _spawn(self):
        rng = self._rng
        self.particles.append({
            'x':  rng.uniform(0, self.W),
            'y':  rng.uniform(-120, -4),
            'vx': rng.uniform(-90, 90),
            'vy': rng.uniform(55, 200),
            'rot': rng.uniform(0, 6.28),
            'rv':  rng.uniform(-6, 6),
            'col': rng.choice(self.COLORS),
            'w':   rng.uniform(6, 16),
            'h':   rng.uniform(4, 10),
            'shape': rng.choice(['rect', 'rect', 'circle', 'ribbon']),
            'a':   255,
        })

    def update(self, dt):
        self.spawn_t += dt
        if self.spawn_t < 4.0:
            for _ in range(4):
                self._spawn()
        for p in self.particles:
            p['x']  += p['vx'] * dt
            p['y']  += p['vy'] * dt
            p['vy'] += 140 * dt
            p['vx'] *= (1 - 0.4 * dt)
            p['rot'] += p['rv'] * dt
            if p['y'] > self.H * 0.75:
                p['a'] = max(0, int(p['a'] - 320 * dt))
        self.particles = [p for p in self.particles
                          if p['a'] > 0 and p['y'] < self.H + 30]

    def draw(self, surf):
        for p in self.particles:
            x, y  = int(p['x']), int(p['y'])
            a     = int(p['a'])
            col   = (*p['col'], a)
            w, h  = max(2, int(p['w'])), max(2, int(p['h']))
            if p['shape'] == 'circle':
                s = pygame.Surface((w*2, w*2), pygame.SRCALPHA)
                pygame.draw.circle(s, col, (w, w), w)
                surf.blit(s, (x-w, y-w))
            else:
                s = pygame.Surface((w, h if p['shape']=='rect' else h*3), pygame.SRCALPHA)
                s.fill(col)
                rot = pygame.transform.rotate(s, math.degrees(p['rot']))
                surf.blit(rot, rot.get_rect(center=(x, y)))


# ═══════════════════════════════════════════════════════════════
class Pulses:
    """Expanding ring pulses emitted from bot center."""
    def __init__(self):
        self.items = []

    def emit(self, x, y, col):
        self.items.append([x, y, 50, 220, col])

    def update(self, dt):
        for p in self.items:
            p[2] += 95 * dt
            p[3] = max(0, int(220 * (1-(p[2]-50)/180)))
        self.items = [p for p in self.items if p[3] > 0]

    def draw(self, surf):
        for x, y, r, a, col in self.items:
            ri = int(r)
            s = pygame.Surface((ri*2+4, ri*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, a), (ri+2, ri+2), ri, 2)
            surf.blit(s, (x-ri-2, y-ri-2))


# ═══════════════════════════════════════════════════════════════
class ScanLine:
    """Horizontal cyan scan line that sweeps the bot periodically."""
    def __init__(self):
        self.y = 0; self.active = False; self.timer = 5.0

    def update(self, dt, top, bot):
        self.timer += dt
        if self.timer > 6.5:
            self.active = True; self.y = top; self.timer = 0
        if self.active:
            self.y += (bot - top) / 0.44 * dt
            if self.y > bot:
                self.active = False

    def draw(self, surf, lx, rx):
        if not self.active: return
        y = int(self.y)
        for dy in range(-4, 5):
            a = max(0, int(105-abs(dy)*20))
            if a > 0:
                s = pygame.Surface((rx-lx, 2), pygame.SRCALPHA)
                s.fill((*CYAN, a))
                surf.blit(s, (lx, y+dy))


# ═══════════════════════════════════════════════════════════════
class Waveform:
    """Animated voice waveform — thin compressed bars, monospace style."""
    BARS = 66
    def __init__(self, rect):
        self.rect = rect
        self.h   = [0.03] * self.BARS
        self.tgt = [0.03] * self.BARS

    def update(self, dt, active, t):
        if active:
            for i in range(self.BARS):
                self.tgt[i] = (abs(math.sin(t*3.5 + i*0.38))*0.55 +
                               abs(math.sin(t*7.1 + i*0.92))*0.35)
        else:
            self.tgt = [0.04] * self.BARS
        for i in range(self.BARS):
            self.h[i] += (self.tgt[i] - self.h[i]) * min(1.0, dt*10)

    def draw(self, surf, active):
        r   = self.rect
        bw  = max(1, r.w // self.BARS)   # bar slot width (maybe 1 or 2 px)
        col = CYAN if active else MUTED
        for i, hv in enumerate(self.h):
            bh = max(2, int(hv * (r.h - 4)))
            bx = r.x + i * bw
            by = r.y + r.h//2 - bh//2
            # 1-px thin line per bar — no gradient fill
            pygame.draw.line(surf, col, (bx, by), (bx, by+bh), 1)


# ═══════════════════════════════════════════════════════════════
class ChatPanel:
    """Animated glassmorphism chat bubble panel."""
    MAX = 18
    def __init__(self, rect):
        self.rect = rect
        self.msgs = []   # {role, lines, anim}
        self.typing = False
        self.type_t = 0.0
        self._fonts = None   # set after pygame.init

    def _get_fonts(self):
        if self._fonts is None:
            self._fonts = {
                'title':  sysfont(13),
                'msg':    sysfont(15),
                'label':  sysfont(12, bold=True),
            }
        return self._fonts

    def add(self, role, text):
        fm = self._get_fonts()['msg']
        max_w = self.rect.w - 90
        words = text.replace('\n', ' ').split()
        lines, cur = [], []
        for w in words:
            test = ' '.join(cur + [w])
            if fm.size(test)[0] > max_w:
                lines.append(' '.join(cur)); cur = [w]
            else:
                cur.append(w)
        if cur: lines.append(' '.join(cur))
        self.msgs.append({'role': role, 'lines': lines or [''], 'anim': 0.0})
        if len(self.msgs) > self.MAX:
            self.msgs.pop(0)

    def update(self, dt, typing):
        self.typing = typing
        self.type_t += dt
        for m in self.msgs:
            m['anim'] = min(1.0, m['anim'] + dt * 5)

    def draw(self, surf):
        fonts  = self._get_fonts()
        fm, fl, ft = fonts['msg'], fonts['label'], fonts['title']
        r = self.rect
        glass_panel(surf, r, BLUE, radius=18, bga=22, ba=90)

        # Panel title
        ts = ft.render("C O N V E R S A T I O N", True, MUTED)
        surf.blit(ts, (r.x + 16, r.y + 10))
        # Separator
        pygame.draw.line(surf, (*MUTED, 60), (r.x+12, r.y+26), (r.right-12, r.y+26))

        lh  = fm.get_height() + 5
        pad = 10
        y   = r.bottom - pad - (32 if self.typing else 6)

        for m in reversed(self.msgs):
            a       = ease_out(m['anim'])
            is_user = (m['role'] == 'user')
            bub_col = BLUE if is_user else PURP
            bub_w   = min(r.w - 80,
                          max(80, max((fm.size(ln)[0] for ln in m['lines']), default=40) + 28))
            bub_h   = len(m['lines']) * lh + 20
            bub_x   = (r.right - bub_w - 12) if is_user else (r.x + 12)
            slide   = int((1-a) * 55 * (1 if is_user else -1))
            bx, by  = bub_x + slide, int(y - bub_h)

            # Bubble background
            bs = pygame.Surface((bub_w, bub_h), pygame.SRCALPHA)
            grad_h(bs, pygame.Rect(0,0,bub_w,bub_h),
                   lerp3(bub_col,(0,0,0),0.55), lerp3(bub_col,(8,8,20),0.65), r=14)
            pygame.draw.rect(bs, (*bub_col, int(145*a)), (0,0,bub_w,bub_h), 2, border_radius=14)
            bs.set_alpha(int(255*a))
            surf.blit(bs, (bx, by))

            # Role label
            lbl = fl.render("YOU" if is_user else "BOT", True, bub_col)
            surf.blit(lbl, (bx + (bub_w - lbl.get_width() - 8 if is_user else 8), by + 4))

            # Message text
            for li, ln in enumerate(m['lines']):
                txt = fm.render(ln, True, WHITE)
                surf.blit(txt, (bx + 12, by + lh*li + 14))

            y = by - 8
            if y < r.y + 30:
                break

        # Typing indicator (three bouncing dots)
        if self.typing:
            ty = r.bottom - pad - 14
            for i in range(3):
                phase = self.type_t * 4 + i * 1.1
                rv = 0.4 + 0.6 * abs(math.sin(phase))
                rc = lerp3(MUTED, CYAN, rv)
                pygame.draw.circle(surf, rc, (r.x + 22 + i*16, ty), int(3 + 2*rv))
