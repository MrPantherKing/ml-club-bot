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
class PixelGrid:
    """
    Smooth, wave-based pixelated shimmer effect.
    A radial sine wave ripples outward from the center, causing grid
    cells to glow in a single colour with smooth transitions.
    """
    GRID_SZ = 28            # must match draw_bg grid size
    COLOR   = (60, 120, 220)  # soft blue-white

    def __init__(self, W, H):
        self.W, self.H = W, H
        self.cols = max(1, W // self.GRID_SZ)
        self.rows = max(1, H // self.GRID_SZ)
        self.cx   = self.cols / 2.0
        self.cy   = self.rows / 2.0
        self.t    = 0.0
        # Pre-create the shared tiny surface
        self._surf = pygame.Surface((self.GRID_SZ - 2, self.GRID_SZ - 2), pygame.SRCALPHA)
        # Pre-compute distances from center for every cell
        self._dist = []
        max_d = math.sqrt(self.cx**2 + self.cy**2) or 1.0
        for gy in range(self.rows):
            row = []
            for gx in range(self.cols):
                d = math.sqrt((gx - self.cx)**2 + (gy - self.cy)**2) / max_d
                row.append(d)
            self._dist.append(row)

    def update(self, dt, t=0):
        self.t += dt

    def draw(self, surf):
        gs  = self.GRID_SZ
        s   = self._surf
        t   = self.t
        col = self.COLOR
        for gy in range(self.rows):
            drow = self._dist[gy]
            for gx in range(self.cols):
                d = drow[gx]
                # Two overlapping sine waves for organic movement
                v = (math.sin(d * 12.0 - t * 1.6) * 0.5
                   + math.sin(d * 8.0 + t * 1.1 + gx * 0.15) * 0.3
                   + math.sin(t * 0.7 + gy * 0.2) * 0.2)
                # Remap to 0-1, then to alpha
                v = max(0.0, (v + 1.0) * 0.5 - 0.30)   # threshold — slightly higher for brighter glow
                a = int(v * 50)   # peak alpha ~50 → more visible
                if a < 1:
                    continue
                px = gx * gs + 1
                py = gy * gs + 1
                s.fill((*col, a))
                surf.blit(s, (px, py))

# backward-compat aliases
FloatDots = PixelGrid
NeuralBG  = PixelGrid


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
        (72,  24,  0.35,  0.15, BLUE,  28,  4),
        (88,  30, -0.25, -0.10, PURP,  22,  3),
        (56,  18,  0.50,  0.22, CYAN,  35,  3),
    ]
    TRAIL_STEPS = 12
    TRAIL_ARC   = 0.40

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

    def draw(self, surf, cx, cy, glow_i=0.2, sf=1.0):
        for i, (rx_base, ry_base, spd, tilt, col, ring_a, pr_base) in enumerate(self._RINGS):
            angle = self.angles[i]
            rx = int(rx_base * sf);  ry = int(ry_base * sf)
            pr = max(2, int(pr_base * sf))

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
    """Soft white glow that sweeps top-to-bottom over the bot."""
    def __init__(self):
        self.y = 0; self.active = False; self.timer = 5.0

    def update(self, dt, top, bot):
        self.timer += dt
        if self.timer > 6.5:
            self.active = True; self.y = top; self.timer = 0
        if self.active:
            self.y += (bot - top) / 0.55 * dt
            if self.y > bot:
                self.active = False

    def draw(self, surf, lx, rx):
        if not self.active: return
        y = int(self.y)
        w = rx - lx
        # Soft white glow band (wider, softer than old cyan line)
        for dy in range(-8, 9):
            a = max(0, int(55 * (1.0 - abs(dy) / 8.0) ** 2))
            if a > 0:
                s = pygame.Surface((w, 1), pygame.SRCALPHA)
                s.fill((255, 255, 255, a))
                surf.blit(s, (lx, y + dy))


# ═══════════════════════════════════════════════════════════════
class Waveform:
    """Animated voice waveform — dynamically scales to container size."""
    BAR_SPACING = 3   # px between bar centers

    def __init__(self, rect):
        self.rect = rect
        self._recompute()

    def _recompute(self):
        """Recalculate bar count from current rect width."""
        self._bars = max(4, self.rect.w // self.BAR_SPACING)
        self.h   = [0.03] * self._bars
        self.tgt = [0.03] * self._bars

    def update(self, dt, active, t):
        # If bar count doesn't match rect, rebuild
        needed = max(4, self.rect.w // self.BAR_SPACING)
        if needed != self._bars:
            self._recompute()
        if active:
            for i in range(self._bars):
                self.tgt[i] = (abs(math.sin(t*3.5 + i*0.38))*0.55 +
                               abs(math.sin(t*7.1 + i*0.92))*0.35)
        else:
            self.tgt = [0.04] * self._bars
        for i in range(self._bars):
            self.h[i] += (self.tgt[i] - self.h[i]) * min(1.0, dt*10)

    def draw(self, surf, active):
        r   = self.rect
        n   = self._bars
        # Distribute bars evenly across rect width
        step = r.w / max(n, 1)
        col  = CYAN if active else MUTED
        for i in range(n):
            hv = self.h[i]
            bh = max(2, int(hv * (r.h - 4)))
            bx = int(r.x + i * step + step * 0.5)
            by = r.y + r.h // 2 - bh // 2
            pygame.draw.line(surf, col, (bx, by), (bx, by + bh), 1)


# ═══════════════════════════════════════════════════════════════
class ChatPanel:
    """Animated glassmorphism chat bubble panel — all sizes scale with sf."""
    MAX = 22
    TEXT_WHITE = (248, 250, 255)

    def __init__(self, rect, sf=1.0):
        self.rect = rect
        self.sf   = sf
        self.msgs = []
        self.typing = False
        self.type_t = 0.0
        self._fonts = None

    def resize(self, new_rect, new_sf):
        """Update rect and scale factor, preserving messages."""
        self.rect = new_rect
        self.sf   = new_sf
        self._fonts = None   # force font rebuild
        # Re-wrap all existing messages for new width
        fm = self._get_fonts()['msg']
        max_w = self.rect.w - int(70 * self.sf)
        for m in self.msgs:
            raw_text = ' '.join(m['lines'])
            words = raw_text.split()
            lines, cur = [], []
            for w in words:
                test = ' '.join(cur + [w])
                if fm.size(test)[0] > max_w:
                    lines.append(' '.join(cur)); cur = [w]
                else:
                    cur.append(w)
            if cur: lines.append(' '.join(cur))
            m['lines'] = lines or ['']

    def _get_fonts(self):
        if self._fonts is None:
            s = self.sf
            self._fonts = {
                'title':  sysfont(max(8, int(15 * s)), bold=True),
                'msg':    sysfont(max(6, int(12 * s))),
                'label':  sysfont(max(5, int(10 * s)), bold=True),
            }
        return self._fonts

    def add(self, role, text):
        fm = self._get_fonts()['msg']
        max_w = self.rect.w - int(70 * self.sf)
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
        fonts = self._get_fonts()
        fm, fl, ft = fonts['msg'], fonts['label'], fonts['title']
        r  = self.rect
        s  = self.sf
        rd = max(6, int(18 * s))
        glass_panel(surf, r, BLUE, radius=rd, bga=16, ba=70)

        # Panel title
        p16 = max(4, int(16 * s));  p12 = max(4, int(12 * s))
        ts = ft.render("C O N V E R S A T I O N", True, (140, 150, 180))
        surf.blit(ts, (r.x + p16, r.y + p12))
        sep_y = r.y + p12 + ts.get_height() + max(2, int(4*s))
        pygame.draw.line(surf, (60, 70, 100, 40), (r.x + int(14*s), sep_y), (r.right - int(14*s), sep_y))

        lh  = fm.get_height() + max(2, int(4 * s))
        pad = max(6, int(14 * s))
        y   = r.bottom - pad - (int(30*s) if self.typing else int(8*s))

        br = max(4, int(12 * s))
        for m in reversed(self.msgs):
            a       = ease_out(m['anim'])
            is_user = (m['role'] == 'user')
            bub_col = BLUE if is_user else PURP
            bub_w   = min(r.w - int(56*s),
                          max(int(70*s), max((fm.size(ln)[0] for ln in m['lines']), default=30) + int(32*s)))
            bub_h   = len(m['lines']) * lh + int(24 * s)
            bub_x   = (r.right - bub_w - int(16*s)) if is_user else (r.x + int(16*s))
            slide   = int((1-a) * 40 * s * (1 if is_user else -1))
            bx, by  = bub_x + slide, int(y - bub_h)

            # Bubble background
            bs = pygame.Surface((bub_w, bub_h), pygame.SRCALPHA)
            grad_h(bs, pygame.Rect(0,0,bub_w,bub_h),
                   lerp3(bub_col,(0,0,0),0.55), lerp3(bub_col,(8,8,20),0.65), r=br)
            pygame.draw.rect(bs, (*bub_col, int(120*a)), (0,0,bub_w,bub_h), 1, border_radius=br)
            bs.set_alpha(int(255*a))
            surf.blit(bs, (bx, by))

            # Role label
            lbl = fl.render("YOU" if is_user else "BOT", True, bub_col)
            lbl_pad = max(4, int(10*s))
            surf.blit(lbl, (bx + (bub_w - lbl.get_width() - lbl_pad if is_user else lbl_pad), by + max(2,int(5*s))))

            # Message text
            for li, ln in enumerate(m['lines']):
                txt = fm.render(ln, True, self.TEXT_WHITE)
                surf.blit(txt, (bx + max(4,int(12*s)), by + lh*li + max(6,int(16*s))))

            y = by - max(6, int(12 * s))
            if y < sep_y + int(8*s):
                break

        # Typing indicator
        if self.typing:
            ty = r.bottom - pad - max(6,int(14*s))
            dot_sp = max(8, int(14*s))
            for i in range(3):
                phase = self.type_t * 4 + i * 1.1
                rv = 0.4 + 0.6 * abs(math.sin(phase))
                rc = lerp3(MUTED, CYAN, rv)
                pygame.draw.circle(surf, rc, (r.x + int(22*s) + i*dot_sp, ty), max(1,int((2 + 2*rv)*s)))
