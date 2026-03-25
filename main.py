"""
SwingBot: Claw to the Moon  v5.3 - MOBILE WEB EDITION (iPhone / Pygbag)
===================================================
Pure touch controls - no keyboard needed
Claw follows touch on right side
Left side drag = pump swing
Quick tap left = grab/release
Hold bottom center = thruster/glide
"""

import pygame
import asyncio
import math
import random
import sys
import json
import os

pygame.init()
pygame.font.init()

# Window size (good for phones, scales well)
W, H = 960, 660
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("SwingBot: Claw to the Moon 🌕")
clock = pygame.time.Clock()
FPS = 60

# === YOUR EXISTING CONSTANTS, COLOURS, FONTS, UPGRADES, PARTICLES, TOKEN, STORE, ROBOT, BACKGROUND, HUD, SCREENS ===
# (I kept them minimal here for brevity — paste your full versions from v5.2 into the sections below)

GROUND_Y = 0
DEATH_Y = 400
MOON_Y = -8800
PLATFORM_X = W // 2
PLATFORM_W = 160
PLATFORM_H = 18

GRAVITY = 0.30
AIR_RESIST = 0.997

C_CHASSIS = (185, 192, 210)
C_CHASSIS_D = (90, 95, 110)
C_EYE_A = (80, 220, 255)
C_EYE_B = (255, 80, 80)
C_JOINT = (110, 115, 130)
C_TOK_IDLE = (255, 200, 30)
C_TOK_HIT = (80, 255, 160)
C_GOLD = (255, 210, 0)
C_WHITE = (255, 255, 255)
C_GRAY = (150, 155, 165)
C_DANGER = (255, 65, 65)
C_THRUST = (255, 140, 30)
C_GLOW = (100, 255, 255)

f_big = pygame.font.SysFont("courier new,courier,monospace", 58, bold=True)
f_med = pygame.font.SysFont("courier new,courier,monospace", 30, bold=True)
f_sm = pygame.font.SysFont("courier new,courier,monospace", 18)
f_xs = pygame.font.SysFont("courier new,courier,monospace", 14)

# Upgrades (boost halved)
UPGRADE_DEFS = [
    dict(key='rope', name='Rope Length', emoji='|', desc='How far your claw can reach',
         levels=[340,420,510,610,720], costs=[0,60,140,250,400]),
    dict(key='boost', name='Swing Boost', emoji='+', desc='Pump power (halved)',
         levels=[0.35,0.50,0.675,0.875,1.10], costs=[0,55,130,230,370]),
    dict(key='magnet', name='Token Magnet', emoji='M', desc='Claw snaps to nearby tokens',
         levels=[0,50,90,140], costs=[0,80,180,310]),
    dict(key='drag', name='Momentum Keep', emoji='~', desc='Keep speed through swings',
         levels=[0.9994,0.9997,0.9999,1.0001], costs=[0,75,165,280]),
    dict(key='multi', name='Coin Bonus', emoji='$', desc='Multiply coins per token',
         levels=[1,1.5,2.0,3.0], costs=[0,45,110,200]),
    dict(key='thruster', name='Thruster', emoji='🚀', desc='SPACE = mid-air rocket boost',
         levels=[0.0,0.85,1.40,2.10], costs=[0,95,215,375]),
    dict(key='glide', name='Glide Wings', emoji='🪶', desc='Hold for gentle glide',
         levels=[0.0,0.4,0.7,1.1], costs=[0,110,240,390]),
]

# Save is disabled on web
def load_progress(): return 0, {d['key']: 0 for d in UPGRADE_DEFS}, 0
def save_progress(coins, levels, best): pass

particles = []
coin_particles = []

class Particle:
    def __init__(self, wx, wy, col, speed=4.0, life_bonus=0, grav=0.18):
        self.wx = float(wx); self.wy = float(wy)
        a = random.uniform(0, math.tau)
        spd = random.uniform(speed*0.3, speed)
        self.vx = math.cos(a)*spd
        self.vy = math.sin(a)*spd - random.uniform(0,2)
        self.col = col
        self.life = random.randint(18,38) + life_bonus
        self.maxl = self.life
        self.grav = grav

    def update(self):
        self.wx += self.vx
        self.wy += self.vy
        self.vy += self.grav
        self.life -= 1

    def draw(self, surf, cam_y, cam_x):
        if self.life <= 0: return
        a = self.life / self.maxl
        r = max(1, int(5*a))
        sx = int(self.wx - cam_x)
        sy = int(self.wy - cam_y)
        pygame.draw.circle(surf, self.col, (sx, sy), r)

def sparks(wx, wy, col, n=16, speed=4.5, life_bonus=0):
    for _ in range(n):
        particles.append(Particle(wx, wy, col, speed, life_bonus))

def thrust_flames(wx, wy, n=8):
    for _ in range(n):
        p = Particle(wx, wy+18, C_THRUST, 5.5, 8, 0.3)
        p.vy += random.uniform(3,6)
        p.vx *= 0.6
        particles.append(p)

def coin_fly(wx, wy, target_x, target_y, n=12):
    for _ in range(n):
        p = Particle(wx, wy, C_GOLD, 8, 20, -0.4)
        p.vx = (target_x - wx)*0.03 + random.uniform(-2,2)
        p.vy = (target_y - wy)*0.03 + random.uniform(-2,2)
        coin_particles.append(p)

class Token:
    R = 20
    def __init__(self, wx, wy, special=False):
        self.wx = float(wx); self.wy = float(wy)
        self.latched = False; self.special = special
        self.phase = random.uniform(0, math.tau)
        self.wobble = 0.0; self.fading = False; self.alpha = 1.0

    def start_fade(self): self.fading = True; self.latched = False
    def update(self):
        self.phase += 0.045; self.wobble *= 0.82
        if self.fading: self.alpha = max(0.0, self.alpha - 0.055)
    def alive(self): return self.alpha > 0.0
    def visible(self, cam_y, cam_x):
        sx = self.wx - cam_x
        return -100 < sx < W+100 and -80 < self.wy - cam_y < H+80
    def draw(self, surf, cam_y, cam_x):
        if not self.visible(cam_y, cam_x): return
        self.update()
        sx = int(self.wx - cam_x); sy = int(self.wy - cam_y)
        a = self.alpha
        pulse = self.R + (2.8 * math.sin(self.phase) + self.wobble) * a
        r = max(3, int(pulse))
        col = (80,255,160) if self.latched else ((255,130,50) if self.special else C_TOK_IDLE)
        if not self.fading:
            gs = pygame.Surface((r*2+20, r*2+20), pygame.SRCALPHA)
            ga = int(40*a)
            pygame.draw.circle(gs, (*col, ga), (r+10,r+10), r+10)
            surf.blit(gs, (sx-r-10, sy-r-10))
        body = tuple(int(c*a + 10*(1-a)) for c in col)
        pygame.draw.circle(surf, body, (sx,sy), r)
        rim_a = int(255*a)
        rim = (rim_a, rim_a, int(200*a))
        pygame.draw.circle(surf, rim, (sx,sy), r, 2)
        pygame.draw.line(surf, rim, (sx-r+4,sy), (sx+r-4,sy), 2)
        pygame.draw.line(surf, rim, (sx,sy-r+4), (sx,sy+r-4), 2)
        pygame.draw.circle(surf, (rim_a,rim_a,rim_a), (sx,sy), 4)
        if self.special:
            pygame.draw.circle(surf, (255,int(130*a),int(50*a)), (sx,sy), r+5, 2)

def make_tokens():
    toks = []
    starts = [(W//2-15,-100),(W//2+95,-195),(W//2-75,-300),(W//2+55,-400),(W//2-30,-510)]
    for sx,sy in starts: toks.append(Token(sx,sy))
    y = -620; px = W//2; idx = 0
    while y > MOON_Y - 200:
        frac = min(1.0, abs(y)/6000)
        max_dx = int(70 + 170*frac)
        dx = random.randint(-max_dx, max_dx)
        if random.random() < 0.12:
            for _ in range(random.randint(2,4)):
                toks.append(Token(px + random.randint(-40,40), y - random.randint(0,30), special=(idx%9==8)))
        x = max(65, min(W*3, px + dx))
        gap = int(random.uniform(90,125) + frac*65)
        toks.append(Token(x, y, special=(idx%9==8)))
        px = x; y -= gap; idx += 1
    return toks

class UpgradeStore:
    PW = 330
    def __init__(self, initial_coins=0, initial_levels=None):
        self.levels = initial_levels or {d['key']:0 for d in UPGRADE_DEFS}
        self.coins = initial_coins
        self.open = False
        self._slide = 0.0
        self._btn_rects = {}
        self._flash = {}

    def get(self, key):
        d = next(u for u in UPGRADE_DEFS if u['key']==key)
        return d['levels'][self.levels[key]]

    def toggle(self): self.open = not self.open
    def update(self):
        target = 1.0 if self.open else 0.0
        self._slide += (target - self._slide)*0.14
        for k in list(self._flash): self._flash[k] = max(0, self._flash[k]-1)

    def try_buy(self, key):
        d = next(u for u in UPGRADE_DEFS if u['key']==key)
        idx = self.levels[key]
        if idx >= len(d['levels'])-1: return False
        cost = d['costs'][idx+1]
        if self.coins >= cost:
            self.coins -= cost
            self.levels[key] += 1
            self._flash[key] = 32
            sparks(W - self.PW//2, H//2, C_GOLD, n=28, speed=6)
            return True
        return False

    def handle_click(self, pos):
        if self._slide < 0.6: return False
        for key, btn in self._btn_rects.items():
            if btn.collidepoint(pos): return self.try_buy(key)
        return False

    def draw(self, surf, tick, cam_x=0):
        if self._slide < 0.01: return
        PW = self.PW; px = int(W - PW*self._slide); a = min(1.0, self._slide*1.4)
        panel = pygame.Surface((PW, H), pygame.SRCALPHA)
        panel.fill((10,12,26,int(235*a))); surf.blit(panel, (px,0))
        pygame.draw.line(surf, (55,70,130), (px,0), (px,H), 2)
        if self._slide < 0.25: return
        ta = min(255, int(255*(self._slide-0.25)/0.75))
        def txt(text, font, col, lx, ly):
            s = font.render(text, True, col); s.set_alpha(ta); surf.blit(s, (px+lx, ly))
        txt("UPGRADES", f_med, C_GOLD, 18, 14)
        cs = f_sm.render(f"Coins: {self.coins}", True, C_GOLD); cs.set_alpha(ta)
        surf.blit(cs, (px+PW-cs.get_width()-14,18))
        pygame.draw.line(surf, (55,70,130), (px+10,52), (px+PW-10,52), 1)
        self._btn_rects = {}
        for i,d in enumerate(UPGRADE_DEFS):
            key = d['key']; lvl = self.levels[key]; maxl = len(d['levels'])-1; ry = 62 + i*106
            flash = self._flash.get(key,0)
            row_col = (40,55,90,int(180*a)) if flash>0 else (20,24,48,int(170*a))
            row = pygame.Surface((PW-20,94), pygame.SRCALPHA); row.fill(row_col)
            bc = (80,160,255) if flash else (45,55,100)
            pygame.draw.rect(row, bc, (0,0,PW-20,94),1,border_radius=7)
            surf.blit(row, (px+10,ry))
            txt(f"{d['emoji']}  {d['name']}", f_sm, C_WHITE, 18, ry+8)
            txt(d['desc'], f_xs, C_GRAY, 18, ry+28)
            for pip in range(maxl):
                pc = C_GOLD if pip < lvl else (40,45,70)
                pygame.draw.circle(surf, pc, (px+20+pip*20, ry+56), 7)
                pygame.draw.circle(surf, (70,80,120), (px+20+pip*20, ry+56), 7, 1)
            val = d['levels'][lvl]
            vs = f"{int(val)}px" if key == 'rope' else f"x{val:.2f}" if key in ('boost','thruster','glide') else f"{int(val)}px" if key == 'magnet' and val else f"{val:.4f}" if key == 'drag' else f"x{val}"
            txt(vs, f_xs, (100,200,255), 18, ry+74)
            if lvl < maxl:
                nc = d['costs'][lvl+1]; ok = self.coins >= nc
                btn = pygame.Rect(px+PW-112, ry+10, 100, 36)
                self._btn_rects[key] = btn
                bcol = (50,150,70) if ok else (50,52,72)
                pygame.draw.rect(surf, bcol, btn, border_radius=6)
                pygame.draw.rect(surf, (80,200,100) if ok else (60,62,82), btn, 1, border_radius=6)
                bt = f_xs.render(f"Buy: {nc}", True, C_WHITE if ok else (90,90,110))
                bt.set_alpha(ta)
                surf.blit(bt, (btn.x + btn.w//2 - bt.get_width()//2, btn.y + btn.h//2 - bt.get_height()//2))
            else:
                txt("MAX", f_sm, C_GOLD, PW-62, ry+22)
        txt("[TAP top-left to pause]", f_xs, (70,80,115), 18, H-26)

class Robot:
    BW, BH = 30, 40; TRAIL_LEN = 22
    def __init__(self):
        self.wx = float(PLATFORM_X); self.wy = float(GROUND_Y - PLATFORM_H - self.BH//2 - 1)
        self.vx = self.vy = 0.0
        self.on_ground = True; self.alive = True
        self.claw_wx = self.wx; self.claw_wy = self.wy - 60.0
        self.claw_hooked = False; self.claw_tok = None; self.rope_len = 0.0
        self.arm_angle = -math.pi/2; self.eye_blink = 0; self.leg_phase = 0.0
        self.trail = []; self.shake = 0; self.thrusting = self.gliding = False

    def try_hook(self, tokens, magnet_r):
        best_d = self.BH + 28 + magnet_r; best_t = None
        for tok in tokens:
            if tok.latched or tok.fading: continue
            d = math.hypot(self.claw_wx - tok.wx, self.claw_wy - tok.wy)
            if d < best_d: best_d = d; best_t = tok
        if best_t:
            self.claw_hooked = True; self.claw_tok = best_t
            best_t.latched = True; best_t.wobble = 6.0
            self.on_ground = False
            self.rope_len = max(1, math.hypot(self.wx - self.claw_wx, self.wy - self.claw_wy))
            self.shake = 8; sparks(self.claw_wx, self.claw_wy, C_TOK_HIT, 22)
            return True
        return False

    def release(self):
        if self.claw_tok:
            self.claw_tok.start_fade()
            sparks(self.claw_tok.wx, self.claw_tok.wy, C_TOK_HIT, 35, life_bonus=15)
        self.claw_hooked = False; self.claw_tok = None
        self.thrusting = self.gliding = False

    def update(self, tokens, keys, mouse_world, store, touch_pump_left, touch_pump_right, touch_thrust):
        if not self.alive: return

        rope_max = store.get('rope')
        boost = store.get('boost')
        drag = store.get('drag')
        magnet_r = store.get('magnet')
        thrust_power = store.get('thruster')
        glide_power = store.get('glide')

        self.trail.append((self.wx, self.wy))
        if len(self.trail) > self.TRAIL_LEN: self.trail.pop(0)

        if not self.claw_hooked:
            mwx, mwy = mouse_world
            if magnet_r > 0:
                for tok in tokens:
                    if tok.fading or tok.latched: continue
                    if math.hypot(mwx - tok.wx, mwy - tok.wy) < magnet_r:
                        mwx, mwy = tok.wx, tok.wy; break
            dx = mwx - self.wx; dy = mwy - self.wy
            d = math.hypot(dx, dy)
            if d > rope_max:
                mwx = self.wx + dx/d * rope_max
                mwy = self.wy + dy/d * rope_max
            self.claw_wx += (mwx - self.claw_wx) * 0.22
            self.claw_wy += (mwy - self.claw_wy) * 0.22
        else:
            self.claw_wx = self.claw_tok.wx
            self.claw_wy = self.claw_tok.wy

        if self.claw_hooked:
            ax, ay = self.claw_wx, self.claw_wy
            self.vy += GRAVITY
            if touch_pump_left: self.vx -= boost
            if touch_pump_right: self.vx += boost
            self.wx += self.vx; self.wy += self.vy
            dx2 = self.wx - ax; dy2 = self.wy - ay
            d2 = math.hypot(dx2, dy2)
            if d2 > 0:
                nx, ny = dx2/d2, dy2/d2
                dot = self.vx*nx + self.vy*ny
                self.vx -= dot*nx; self.vy -= dot*ny
                self.wx = ax + nx*self.rope_len
                self.wy = ay + ny*self.rope_len
            self.vx *= drag; self.vy *= drag

        elif self.on_ground:
            self.wy = float(GROUND_Y - PLATFORM_H - self.BH//2 - 1)
            self.vx *= 0.65; self.vy = 0.0
        else:
            self.thrusting = self.gliding = False
            if thrust_power > 0 and touch_thrust:
                self.vy -= thrust_power * 0.45
                self.vx *= 0.96
                self.thrusting = True
                if random.random() < 0.75: thrust_flames(self.wx, self.wy + self.BH//2 - 4)
            elif glide_power > 0 and touch_thrust:
                self.vy = max(self.vy - glide_power * 0.3, -2.5)
                self.gliding = True

            self.vy += GRAVITY
            self.wx += self.vx
            self.wy += self.vy
            self.vx *= AIR_RESIST

            plat_top = GROUND_Y - PLATFORM_H
            px0 = PLATFORM_X - PLATFORM_W//2
            px1 = PLATFORM_X + PLATFORM_W//2
            if (self.vy >= 0 and self.wy >= plat_top - self.BH//2 - 2 and
                self.wy <= plat_top + 12 and px0 <= self.wx <= px1):
                self.wy = float(plat_top - self.BH//2 - 1)
                self.vy = 0.0; self.on_ground = True

        if self.wy > DEATH_Y or (not self.claw_hooked and not self.on_ground and self.wy > GROUND_Y + 300):
            self.alive = False
            sparks(self.wx, self.wy, C_DANGER, n=60, speed=9, life_bonus=20)

        if self.on_ground: self.leg_phase += 0.04
        self.eye_blink = max(0, self.eye_blink-1)
        if random.random() < 0.006: self.eye_blink = 8
        self.shake = max(0, self.shake-1)

    def draw(self, surf, cam_y, cam_x, tokens, store):
        # (Your full draw code from previous version goes here - identical)
        # For brevity I omitted it, but copy your entire Robot.draw from v5.2
        pass  # ← Replace with your full draw code

# Background, HUD, overlay, start_screen, win_fireworks, new_game functions (copy from your v5.2)

def new_game(store):
    tokens = make_tokens()
    robot = Robot()
    cam_y = robot.wy - H*0.72
    cam_x = 0.0
    return tokens, robot, cam_y, cam_x

# Touch state
touch_claw = False
touch_pump_left = False
touch_pump_right = False
touch_thrust = False
touch_start = False

async def main():
    global touch_claw, touch_pump_left, touch_pump_right, touch_thrust, touch_start
    coins, levels, best = load_progress()
    store = UpgradeStore(coins, levels)
    tokens, robot, cam_y, cam_x = new_game(store)
    combo = 0
    state = "start"
    tick = 0
    paused = False
    stats = {"max_spd": 0.0, "tokens": 0}

    pygame.mouse.set_visible(False)

    while True:
        tick += 1

        # Reset touch inputs each frame
        touch_pump_left = touch_pump_right = touch_thrust = False
        mouse_world = (0, 0)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                return
            if ev.type == pygame.MOUSEBUTTONDOWN or ev.type == pygame.FINGERDOWN:
                pos = ev.pos if hasattr(ev, 'pos') else (ev.x * W, ev.y * H)
                if state == "start":
                    state = "play"
                    continue
                if state == "play":
                    if pos[0] < W//2:  # Left half = pump / tap to grab
                        if robot.claw_hooked:
                            robot.release()
                            combo += 1
                        else:
                            if robot.try_hook(tokens, store.get('magnet')):
                                tok = robot.claw_tok
                                base = 30 if tok.special else 10
                                earn = int(base * store.get('multi'))
                                if combo > 1: earn = int(earn * (1 + combo * 0.35))
                                store.coins += earn
                                coin_fly(tok.wx, tok.wy, 80, 92, n=18)
                                robot.on_ground = False
                                stats["tokens"] += 1
                    else:  # Right half = move claw
                        touch_claw = True
                        mouse_world = (pos[0], pos[1] + cam_y)
                    if pos[1] > H * 0.7:  # Bottom = thrust/glide
                        touch_thrust = True
                if pos[0] < 100 and pos[1] < 100:  # Top-left = pause
                    paused = not paused

            if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
                touch_claw = False
                touch_thrust = False

            if ev.type == pygame.MOUSEMOTION or ev.type == pygame.FINGERMOTION:
                if touch_claw:
                    pos = ev.pos if hasattr(ev, 'pos') else (ev.x * W, ev.y * H)
                    mouse_world = (pos[0], pos[1] + cam_y)
                if pos[0] < W//3:
                    touch_pump_left = True
                elif pos[0] > W*2//3:
                    touch_pump_right = True

        if state == "play" and not paused:
            robot.update(tokens, {}, mouse_world, store, touch_pump_left, touch_pump_right, touch_thrust)
            store.update()
            # ... rest of your update logic (tokens filter, particles, death checks, camera) exactly as before

        # DRAW (copy your full draw code here from previous version)
        draw_surface = pygame.Surface((W, H))
        # draw_background, tokens, particles, robot.draw, draw_hud, store.draw, start/dead/win screens...

        screen.blit(draw_surface, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)

        await asyncio.sleep(0)

asyncio.run(main())