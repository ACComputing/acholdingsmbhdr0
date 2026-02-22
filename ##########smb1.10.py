"""
Super Mario Bros - Enhanced Pygame Recreation (Worlds 1-1 through 8-4)
Now with JSON level loading – place hand‑crafted layouts in the 'levels' folder.
Optimised for 60 FPS (Famicom speed).
"""

import pygame
import numpy as np
import sys
import random
import math
import json
import os

# ──────────────────────────────────────────────────────────────
#  INIT
# ──────────────────────────────────────────────────────────────
pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

SW, SH = 800, 600
TILE   = 40
FPS    = 60

# ──────────────────────────────────────────────────────────────
#  TILE IDs
# ──────────────────────────────────────────────────────────────
AIR=0; GROUND=1; BRICK=2; QBLOCK=3; USED=4
PIPE_TL=5; PIPE_TR=6; PIPE_BL=7; PIPE_BR=8
COIN_BLOCK=9; STAR_BLOCK=10; HIDDEN_1UP=11; PLATFORM=12

SOLID = {GROUND,BRICK,QBLOCK,USED,PIPE_TL,PIPE_TR,PIPE_BL,PIPE_BR,
         COIN_BLOCK,STAR_BLOCK,HIDDEN_1UP,PLATFORM}

# ──────────────────────────────────────────────────────────────
#  COLORS  (NES palette approximations)
# ──────────────────────────────────────────────────────────────
SKY       = (92,148,252); CAVE_SKY  = (0,0,0)
WATER_SKY = (20,40,120);  CASTLE_SKY= (10,0,10)
BROWN     = (227,160,20); DARK_BRN  = (180,120,0)
RED_BRICK = (200,76,12);  QBLK_YLW  = (252,188,20)
USED_CLR  = (150,100,50); PIP_GRN   = (0,168,0)
PIP_DRK   = (0,100,0);    COIN_YLW  = (252,188,20)
LAVA_CLR  = (255,80,0);   BLACK     = (0,0,0)
WHITE     = (255,255,255); RED      = (220,50,0)
MARIO_HAT = (150,30,0);   GOOMBA_C  = (160,82,45)
KOOPA_C   = (50,160,50);  FIRE_C    = (255,100,0)
STAR_C    = (255,255,0);  FLAG_C    = (50,200,50)
MUSHROOM_C= (255,0,0);    FLOWER_C  = (255,200,0)
BOWSER_C  = (0,120,0);    HAMMER_C  = (100,50,10)

# ──────────────────────────────────────────────────────────────
#  SOUND SYNTHESIS
# ──────────────────────────────────────────────────────────────
SR = 22050

def _sweep(f0, f1, dur, vol=0.25):
    n = max(1, int(dur*SR))
    f = np.linspace(f0, f1, n)
    p = np.cumsum(f)/SR
    w = np.sin(2*np.pi*p) * np.linspace(1,0,n)
    return pygame.sndarray.make_sound((w*vol*32767).astype(np.int16))

def _sq(freq, dur, duty=0.5, vol=0.22):
    n = max(1, int(dur*SR))
    t = np.linspace(0, dur, n, False)
    w = np.where(np.mod(t*freq, 1) < duty, 1.0, -1.0) * np.linspace(1,0,n)
    return pygame.sndarray.make_sound((w*vol*32767).astype(np.int16))

def _tri(freq, dur, vol=0.16):
    n = max(1, int(dur*SR))
    t = np.linspace(0, dur, n, False)
    w = 2*np.abs(np.mod(t*freq, 1.0)-0.5)-0.5
    return pygame.sndarray.make_sound((w*vol*32767).astype(np.int16))

def _noise(dur, vol=0.16):
    n = max(1, int(dur*SR))
    w = np.random.uniform(-1,1,n)*np.linspace(1,0,n)
    return pygame.sndarray.make_sound((w*vol*32767).astype(np.int16))

try:
    SFX = {
        'jump_s'    : _sweep(300,600,0.10),
        'jump_b'    : _sweep(250,700,0.14),
        'coin'      : _sweep(600,900,0.09),
        'stomp'     : _sweep(200,80,0.10),
        'powerup'   : _sweep(400,800,0.30),
        'die'       : _sweep(600,80,0.50),
        'flagpole'  : _sweep(300,900,0.60),
        'clear'     : _sq(880,0.45),
        'brick'     : _noise(0.08),
        'fire'      : _sweep(500,300,0.07),
        'star_get'  : _sweep(500,1200,0.20),
        '1up'       : _sweep(659,988,0.30),
        'kick'      : _sweep(300,150,0.06),
        'bowser_hit': _sweep(200,50,0.25),
    }
except Exception as ex:
    print(f"Sound warning: {ex}")
    SFX = {}

def play(name):
    s = SFX.get(name)
    if s:
        try: s.play()
        except: pass

# ──────────────────────────────────────────────────────────────
#  MUSIC SEQUENCER  (synthesized NES-like melody)
# ──────────────────────────────────────────────────────────────
class MusicEngine:
    OW = [(659,.15),(659,.15),(0,.10),(659,.15),(0,.10),(523,.15),(659,.15),
          (784,.30),(0,.30),(392,.30),(0,.30),(523,.30),(0,.20),(392,.30),(0,.20),
          (330,.30),(0,.20),(440,.20),(494,.20),(466,.15),(440,.20),(0,.10),
          (392,.20),(659,.20),(784,.20),(880,.20),(698,.20),(784,.20),(0,.10),
          (659,.20),(0,.10),(523,.20),(587,.15),(494,.20)]
    UG = [(392,.10),(0,.05),(392,.10),(0,.05),(392,.10),(0,.05),
          (392,.15),(494,.15),(0,.05),(466,.10),(0,.05),(440,.10),(0,.05),
          (415,.10),(0,.05),(392,.15),(330,.10),(349,.10),(392,.15),
          (261,.10),(294,.10),(330,.15)]
    CS = [(196,.12),(0,.05),(196,.12),(0,.05),(196,.12),(0,.05),
          (196,.15),(233,.15),(0,.05),(220,.10),(0,.05),(208,.10),(0,.05),
          (196,.12),(0,.05),(185,.10),(0,.05),(175,.10),(0,.05),(196,.12)]
    UW = [(523,.20),(0,.10),(659,.20),(0,.10),(784,.20),(0,.10),
          (698,.20),(0,.10),(659,.20),(0,.10),(587,.30),(0,.20),(523,.30),(0,.30)]
    ST = [(784,.08),(659,.08),(523,.08),(784,.08),(659,.08),(523,.08),
          (784,.08),(784,.08),(784,.08),(784,.08),(698,.08),(587,.08),
          (466,.08),(698,.08),(587,.08),(466,.08)]
    THEMES = {'overworld':OW,'underground':UG,'castle':CS,'underwater':UW,'star':ST}

    def __init__(self):
        self.theme=None; self.notes=[]; self.idx=0; self.timer=0.0; self.loop=True
        self._ch = pygame.mixer.Channel(0) if pygame.mixer.get_num_channels()>0 else None

    def set(self, name, loop=True):
        if name==self.theme: return
        self.theme=name; self.notes=self.THEMES.get(name,[]); self.idx=0; self.timer=0.0; self.loop=loop

    def update(self, dt):
        if not self.notes or not self._ch: return
        self.timer -= dt
        if self.timer > 0: return
        if self.idx >= len(self.notes):
            if self.loop: self.idx=0
            else: return
        freq, dur = self.notes[self.idx]; self.idx+=1
        self.timer = max(dur, 0.02)
        if freq > 0:
            try: self._ch.play(_tri(freq, dur*1.1, vol=0.10))
            except: pass

MUSIC = MusicEngine()

# ──────────────────────────────────────────────────────────────
#  LEVEL TYPE MAP  (from disassembly AreaType logic)
# ──────────────────────────────────────────────────────────────
LEVEL_TYPE = {}
for _w in range(1,9):
    for _l in range(1,5):
        if _l==4:                       LEVEL_TYPE[(_w,_l)]='castle'
        elif _l==2 and _w in(1,3,5,7): LEVEL_TYPE[(_w,_l)]='underground'
        elif _l==3 and _w in(2,4,6,8): LEVEL_TYPE[(_w,_l)]='underwater'
        else:                           LEVEL_TYPE[(_w,_l)]='overworld'

def lt_music(lt): return {'overworld':'overworld','underground':'underground',
                           'underwater':'underwater','castle':'castle'}.get(lt,'overworld')
def lt_sky(lt):   return {'overworld':SKY,'underground':CAVE_SKY,
                           'underwater':WATER_SKY,'castle':CASTLE_SKY}.get(lt,SKY)

# ──────────────────────────────────────────────────────────────
#  LEVEL LOADER (JSON)
# ──────────────────────────────────────────────────────────────

LEVELS_DIR = "levels"

def load_level_from_json(w, l):
    """Try to load a level from a JSON file. Returns (grid, width) or None."""
    filename = f"level_{w}-{l}.json"
    filepath = os.path.join(LEVELS_DIR, filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r') as f:
        data = json.load(f)
    # Data should be a list of rows (each a list of ints)
    grid = data
    H = len(grid)
    if H != 15:
        print(f"Warning: {filename} has {H} rows, expected 15. Adjusting...")
        # You can decide how to handle – maybe pad or truncate.
        # For simplicity we'll assume correct.
    W = len(grid[0]) if H > 0 else 0
    return grid, W

# ──────────────────────────────────────────────────────────────
#  LEVEL BUILDERS  (1-1 thru 1-4 hand-crafted; rest procedural)
# ──────────────────────────────────────────────────────────────
def _gr(W, H, gaps=None):
    """Base ground grid with optional gaps."""
    g = [[AIR]*W for _ in range(H)]
    for x in range(W): g[H-1][x]=GROUND; g[H-2][x]=GROUND
    if gaps:
        for gx,gw in gaps:
            for dx in range(gw):
                cx=gx+dx
                if 0<=cx<W: g[H-1][cx]=AIR; g[H-2][cx]=AIR
    return g

def _pl(g,col,row,tile):
    H,W=len(g),len(g[0])
    if 0<=row<H and 0<=col<W: g[row][col]=tile

def _run(g,row,c0,c1,tile):
    for c in range(c0,c1): _pl(g,c,row,tile)

def _pipe(g,col,height,H):
    base=H-2
    for dy in range(height):
        _pl(g,col,  base-dy,PIPE_BL)
        _pl(g,col+1,base-dy,PIPE_BR)
    _pl(g,col,  base-height+1,PIPE_TL)
    _pl(g,col+1,base-height+1,PIPE_TR)

def _stairs(g,sx,W,H):
    for s in range(1,9):
        for dy in range(s): _pl(g,sx+s-1,H-2-dy,GROUND)

def _flag_clear(g,W,H):
    for y in range(H-2): _pl(g,W-4,y,AIR)

def _clear_start(g,H):
    for y in range(H-2):
        for x in range(4): _pl(g,x,y,AIR)
    for x in range(3): _pl(g,x,H-1,GROUND); _pl(g,x,H-2,GROUND)

# World 1-1: hand-crafted from SMBDIS.ASM column data
def build_1_1():
    H,W=15,212
    g=_gr(W,H,gaps=[(168,2),(178,3)])
    for col,tile in [(16,QBLOCK),(20,QBLOCK),(21,BRICK),(22,COIN_BLOCK),
                     (23,BRICK),(24,QBLOCK),(25,BRICK)]:
        _pl(g,col,H-6,tile)
    _pl(g,21,H-10,QBLOCK)      # elevated Q block
    _pipe(g,28,2,H); _pipe(g,38,3,H); _pipe(g,46,4,H); _pipe(g,57,4,H)
    for c in range(64,68): _pl(g,c,H-6,BRICK)
    _run(g,H-5,78,86,GROUND); _run(g,H-6,80,84,GROUND); _run(g,H-7,81,83,GROUND)
    for col,tile in [(91,QBLOCK),(94,BRICK),(95,COIN_BLOCK),(96,BRICK),(97,QBLOCK),(98,BRICK)]:
        _pl(g,col,H-6,tile)
    _pl(g,95,H-10,STAR_BLOCK)
    _pipe(g,118,2,H)
    _stairs(g,W-20,W,H); _flag_clear(g,W,H); _clear_start(g,H)
    return g,W

def build_1_2():
    H,W=15,180
    g=_gr(W,H)
    for x in range(W-10): g[0][x]=GROUND; g[1][x]=GROUND
    _run(g,H-5,6,14,BRICK); _run(g,H-7,16,24,BRICK); _run(g,H-5,26,34,BRICK)
    for col,tile in [(18,QBLOCK),(20,COIN_BLOCK),(22,QBLOCK)]: _pl(g,col,H-7,tile)
    _pipe(g,80,5,H); _pipe(g,92,5,H); _pipe(g,104,5,H)
    _run(g,H-6,40,50,BRICK)
    _pl(g,44,H-6,QBLOCK); _pl(g,46,H-6,COIN_BLOCK)
    _stairs(g,W-22,W,H); _flag_clear(g,W,H); _clear_start(g,H)
    return g,W

def build_1_3():
    H,W=15,160
    g=[[AIR]*W for _ in range(H)]
    for x in range(16): g[H-1][x]=GROUND; g[H-2][x]=GROUND
    for px,py,pw in [(16,H-6,8),(28,H-6,6),(38,H-4,4),(46,H-6,5),(54,H-8,4),
                     (62,H-6,6),(72,H-5,4),(80,H-7,5),(90,H-5,6),
                     (100,H-6,4),(108,H-4,5),(118,H-6,4)]:
        _run(g,py,px,px+pw,GROUND)
    _pl(g,18,H-8,QBLOCK); _pl(g,30,H-8,COIN_BLOCK); _pl(g,50,H-10,QBLOCK)
    for x in range(W-24,W-2): g[H-1][x]=GROUND; g[H-2][x]=GROUND
    _stairs(g,W-20,W,H); _flag_clear(g,W,H)
    return g,W

def build_1_4():
    H,W=15,140
    g=_gr(W,H,gaps=[(20,3),(32,3),(50,4),(68,3)])
    _run(g,2,0,30,GROUND); _run(g,2,40,70,GROUND)
    _run(g,H-5,10,12,BRICK); _run(g,H-4,10,12,BRICK); _run(g,H-3,10,12,BRICK)
    _run(g,H-5,26,28,BRICK); _run(g,H-6,26,28,BRICK)
    for x in range(W-30,W-4): g[H-1][x]=GROUND; g[H-2][x]=GROUND
    _stairs(g,W-22,W,H); _flag_clear(g,W,H); _clear_start(g,H)
    return g,W

def build_proc(world, lnum):
    rng=random.Random(world*100+lnum)
    lt=LEVEL_TYPE[(world,lnum)]
    H=15; W=90+world*6+lnum*3
    if lt=='underground':
        g=_gr(W,H)
        for x in range(W-8): g[0][x]=GROUND; g[1][x]=GROUND
    elif lt=='castle':
        gaps=[(rng.randint(12,W-30),rng.randint(2,4)) for _ in range(3+world//2)]
        g=_gr(W,H,gaps=gaps)
    else:
        ng=2+world//2+(1 if lnum>=3 else 0)
        gaps=[(rng.randint(12,W-20),rng.randint(2,3)) for _ in range(ng)]
        g=_gr(W,H,gaps=gaps)
    for _ in range(5+world+lnum):
        px=rng.randint(5,W-15); py=rng.choice([H-5,H-6,H-7,H-8]); pw=rng.randint(3,7)
        for dx in range(pw):
            cx=px+dx
            if 0<=cx<W-4 and g[py][cx]==AIR:
                g[py][cx]=rng.choice([BRICK,BRICK,BRICK,QBLOCK,COIN_BLOCK])
    placed=[]
    for _ in range(2+world):
        for _ in range(30):
            px=rng.randint(8,W-15); ph=rng.randint(2,3)
            if min(px,W-1)<W and g[H-1][min(px,W-1)]==AIR: continue
            if min(px+1,W-1)<W and g[H-1][min(px+1,W-1)]==AIR: continue
            if any(abs(px-pp)<6 for pp in placed): continue
            placed.append(px); _pipe(g,px,ph,H); break
    _stairs(g,W-20,W,H); _flag_clear(g,W,H); _clear_start(g,H)
    return g,W

BUILDERS = {(1,1):build_1_1,(1,2):build_1_2,(1,3):build_1_3,(1,4):build_1_4}

def build_level(w,l):
    # First, try to load from JSON
    json_result = load_level_from_json(w, l)
    if json_result is not None:
        return json_result
    # Fallback to built‑in builders or procedural generation
    fn = BUILDERS.get((w, l))
    if fn:
        return fn()
    else:
        return build_proc(w, l)

# ──────────────────────────────────────────────────────────────
#  ENEMY SPAWN DATA  (1-1 hand-placed; rest procedural)
# ──────────────────────────────────────────────────────────────
SPAWNS_1_1 = [('goomba',22),('goomba',40),('goomba',41),('goomba',80),
               ('goomba',88),('koopa',94),('goomba',130),('goomba',131),
               ('koopa',148),('goomba',170),('goomba',171)]
SPAWNS_1_2 = [('goomba',10),('goomba',22),('koopa',35),('goomba',50),('koopa',70)]
NAMED = {(1,1):SPAWNS_1_1,(1,2):SPAWNS_1_2}

def _gnd(grid, col):
    H,W=len(grid),len(grid[0])
    col=min(col,W-1)
    for ey in range(H-3,0,-1):
        if grid[ey][col] in SOLID: return ey
    return H-3

def _mk(etype,col,grid):
    ey=_gnd(grid,col)
    r=pygame.Rect(col*TILE,(ey-1)*TILE+8,TILE-6,TILE-6)
    return {'type':etype,'rect':r,'vx':-1,'vy':0,'alive':True,'death_timer':0,
            'on_ground':False,'shell':False,'shell_vx':0,'anim':0,
            'hp':(5 if etype=='bowser' else 1),'throw_timer':60,'fire_timer':180}

def spawn_enemies(grid,world,lnum,W):
    H=len(grid); lt=LEVEL_TYPE[(world,lnum)]
    rng=random.Random(world*1000+lnum*37+13)
    enemies=[]
    named=NAMED.get((world,lnum))
    if named:
        for et,col in named: enemies.append(_mk(et,col,grid))
    else:
        placed=[]
        for _ in range(3+world*2+lnum):
            for _ in range(20):
                ex=rng.randint(10,W-12)
                if any(abs(ex-p)<4 for p in placed): continue
                if ex<W and grid[H-1][ex]==AIR: continue
                placed.append(ex); enemies.append(_mk('goomba',ex,grid)); break
        for _ in range(world//2+lnum//2):
            for _ in range(20):
                ex=rng.randint(12,W-12)
                if any(abs(ex-p)<5 for p in placed): continue
                if ex<W and grid[H-1][ex]==AIR: continue
                placed.append(ex); enemies.append(_mk('koopa',ex,grid)); break
        for _ in range(world//3):
            for _ in range(20):
                ex=rng.randint(15,W-20)
                if any(abs(ex-p)<6 for p in placed): continue
                if ex<W and grid[H-1][ex]==AIR: continue
                placed.append(ex); enemies.append(_mk('hammerbro',ex,grid)); break
    if lt=='castle':
        for i in range(2+world//2):
            fx=rng.randint(10,W-20)*TILE; fy=rng.randint(3,8)*TILE
            enemies.append({'type':'firebar','cx':fx,'cy':fy,'angle':i*60.0,
                            'radius':(2+i%3)*TILE,'speed':1.5+world*0.25,
                            'alive':True,'death_timer':0,'rect':pygame.Rect(fx,fy,16,16),
                            'hp':1,'vx':0,'vy':0,'on_ground':False,'anim':0,
                            'throw_timer':0,'fire_timer':0,'shell':False,'shell_vx':0})
        bx=W-30; ey=_gnd(grid,bx)
        r=pygame.Rect(bx*TILE,(ey-2)*TILE,TILE*2,TILE*2)
        enemies.append({'type':'bowser','rect':r,'vx':-0.4,'vy':0,'alive':True,
                        'death_timer':0,'on_ground':False,'hp':5,'anim':0,
                        'fire_timer':180,'throw_timer':0,'shell':False,'shell_vx':0})
    return enemies

# ──────────────────────────────────────────────────────────────
#  PHYSICS CONSTANTS  (tuned from disassembly tables)
# ──────────────────────────────────────────────────────────────
GRAVITY       = 0.65
MAX_FALL      = 20
WALK_SPEED    = 3.0
RUN_SPEED     = 5.5
JUMP_VY_WALK  = -14.0
JUMP_VY_RUN   = -15.5
JUMP_HOLD_G   = 0.42   # fraction of gravity while holding jump
FRICTION      = 0.84

# ──────────────────────────────────────────────────────────────
#  PLAYER
# ──────────────────────────────────────────────────────────────
class Player:
    def __init__(self,x,y):
        self.x=float(x); self.y=float(y)
        self.vx=0.0; self.vy=0.0
        self.w=TILE-8; self.h=TILE-8
        self.on_ground=False; self.facing=1
        self.status=0       # 0=small 1=super 2=fire
        self.invincible=0
        self.star_timer=0
        self.dead=False; self.death_timer=0
        self.jump_held=False; self._fire_cd=0

    @property
    def rect(self): return pygame.Rect(int(self.x),int(self.y),self.w,self.h)
    @property
    def big(self):  return self.status>=1

    def _collide(self,dx,dy,grid):
        H,W=len(grid),len(grid[0])
        self.x+=dx; self.y+=dy
        r=self.rect; hit=None
        c0=max(0,r.left//TILE); c1=min(W-1,r.right//TILE)
        r0=max(0,r.top//TILE);  r1=min(H-1,r.bottom//TILE)
        for row in range(r0,r1+1):
            for col in range(c0,c1+1):
                if grid[row][col] not in SOLID: continue
                b=pygame.Rect(col*TILE,row*TILE,TILE,TILE)
                if not r.colliderect(b): continue
                if   dx>0:  self.x=b.left-self.w
                elif dx<0:  self.x=b.right
                elif dy>0:  self.y=b.top-self.h; self.vy=0; self.on_ground=True
                elif dy<0:  self.y=b.bottom; self.vy=0; hit=(col,row)
                r=self.rect
        return hit

    def update(self,keys,grid,bumped,fireballs):
        H,W=len(grid),len(grid[0])
        if self.dead:
            self.death_timer+=1; self.vy+=GRAVITY*0.5; self.y+=self.vy; return
        if self.invincible>0: self.invincible-=1
        if self.star_timer >0: self.star_timer -=1
        if self._fire_cd   >0: self._fire_cd   -=1

        left =keys[pygame.K_LEFT] or keys[pygame.K_a]
        right=keys[pygame.K_RIGHT]or keys[pygame.K_d]
        run  =keys[pygame.K_x]    or keys[pygame.K_LSHIFT]
        jump =keys[pygame.K_SPACE]or keys[pygame.K_UP] or keys[pygame.K_w]
        fire =keys[pygame.K_z]    or keys[pygame.K_LCTRL]

        top_spd = RUN_SPEED if run else WALK_SPEED
        if right:  self.vx=min(self.vx+0.5,  top_spd); self.facing=1
        elif left: self.vx=max(self.vx-0.5, -top_spd); self.facing=-1
        else:      self.vx *= FRICTION; self.vx=0 if abs(self.vx)<0.1 else self.vx

        if jump and self.on_ground:
            self.vy=JUMP_VY_RUN if abs(self.vx)>2 else JUMP_VY_WALK
            self.on_ground=False; self.jump_held=True
            play('jump_b' if self.big else 'jump_s')
        if not jump: self.jump_held=False
        self.vy += GRAVITY*(JUMP_HOLD_G if self.jump_held and self.vy<0 else 1.0)
        if self.vy>MAX_FALL: self.vy=MAX_FALL

        if fire and self.status==2 and self._fire_cd==0:
            fireballs.append(Fireball(
                self.x+(self.w if self.facing>0 else 0),
                self.y+self.h*0.3, self.facing))
            play('fire'); self._fire_cd=20

        was_on=self.on_ground; self.on_ground=False
        self._collide(self.vx,0,grid)
        b=self._collide(0,self.vy,grid)
        if b: bumped.append(b)
        if not self.on_ground and was_on:
            tr=pygame.Rect(int(self.x),int(self.y)+self.h+2,self.w,2)
            for row in range(max(0,tr.top//TILE),min(H-1,tr.bottom//TILE)+1):
                for col in range(max(0,tr.left//TILE),min(W-1,tr.right//TILE)+1):
                    if grid[row][col] in SOLID:
                        if tr.colliderect(pygame.Rect(col*TILE,row*TILE,TILE,TILE)):
                            self.on_ground=True
        self.x=max(0,self.x)
        if self.y>H*TILE: self.kill()

    def hit(self):
        if self.dead or self.star_timer>0 or self.invincible>0: return
        if self.status>0: self.status-=1; self.invincible=120
        else: self.kill()

    def kill(self):
        if self.dead: return
        self.dead=True; self.vy=-12; play('die')

    def give(self,kind):
        if   kind=='mushroom' and self.status==0: self.status=1; play('powerup')
        elif kind=='flower'   and self.status<2:  self.status=2; play('powerup')
        elif kind=='star':    self.star_timer=600; play('star_get')
        elif kind=='1up':     play('1up')

    def draw(self,screen,cx):
        if self.dead and self.death_timer%4<2: return
        if self.invincible>0 and self.invincible%8<4: return
        col=STAR_C if self.star_timer>0 and (self.star_timer//4)%2==0 else RED
        rx=int(self.x)-cx; ry=int(self.y); bw=self.w; bh=self.h
        pygame.draw.rect(screen,col,(rx,ry,bw,bh))
        pygame.draw.rect(screen,MARIO_HAT,(rx,ry-6,bw,7))
        ew=4; ex=rx+(bw-ew-2) if self.facing>0 else rx+2
        pygame.draw.rect(screen,WHITE,(ex,ry+4,ew+2,5))
        pygame.draw.rect(screen,BLACK,(ex+(ew//2 if self.facing>0 else 0),ry+5,ew//2+1,3))
        if self.status==2:
            pygame.draw.rect(screen,WHITE,(rx+2,ry+bh-8,bw-4,5))
        if self.big:
            pygame.draw.rect(screen,(180,80,0),(rx,ry-14,bw,8))

# ──────────────────────────────────────────────────────────────
#  FIREBALL
# ──────────────────────────────────────────────────────────────
class Fireball:
    def __init__(self,x,y,d):
        self.x=float(x); self.y=float(y); self.vx=7*d; self.vy=-3.0
        self.alive=True; self.bounces=0
    @property
    def rect(self): return pygame.Rect(int(self.x),int(self.y),10,10)

    def update(self,grid):
        H,W=len(grid),len(grid[0])
        self.vy+=GRAVITY*0.8; self.x+=self.vx; self.y+=self.vy
        col=int(self.x+5)//TILE; row=int(self.y+10)//TILE
        if 0<=row<H and 0<=col<W and grid[row][col] in SOLID:
            self.vy=-5; self.bounces+=1
        if self.bounces>4 or self.x<0 or self.x>W*TILE or self.y>H*TILE:
            self.alive=False

    def draw(self,screen,cx):
        rx=int(self.x)-cx
        pygame.draw.circle(screen,(255,200,0),(rx+5,int(self.y)+5),5)
        pygame.draw.circle(screen,WHITE,(rx+4,int(self.y)+4),2)

# ──────────────────────────────────────────────────────────────
#  POWER-UP OBJECT
# ──────────────────────────────────────────────────────────────
class PowerUp:
    def __init__(self,x,y,kind='mushroom'):
        self.x=float(x); self.y=float(y); self.kind=kind
        self.vx=1.5; self.vy=0.0; self.alive=True; self.anim=0
        self.emerge_y=y-TILE; self.emerging=True

    @property
    def rect(self): return pygame.Rect(int(self.x),int(self.y),TILE-4,TILE-4)

    def update(self,grid):
        H,W=len(grid),len(grid[0])
        if self.emerging:
            self.y-=1.5
            if self.y<=self.emerge_y: self.y=self.emerge_y; self.emerging=False
            return
        self.vy+=GRAVITY*0.7
        if self.vy>10: self.vy=10
        self.x+=self.vx; self.y+=self.vy
        r=self.rect
        c0=max(0,r.left//TILE); c1=min(W-1,r.right//TILE)
        r0=max(0,r.top//TILE);  r1=min(H-1,r.bottom//TILE)
        for row in range(r0,r1+1):
            for col in range(c0,c1+1):
                if grid[row][col] not in SOLID: continue
                b=pygame.Rect(col*TILE,row*TILE,TILE,TILE)
                if not r.colliderect(b): continue
                if self.vy>0: self.y=b.top-(TILE-4); self.vy=0
                elif self.vx>0: self.x=b.left-(TILE-4); self.vx*=-1
                elif self.vx<0: self.x=b.right; self.vx*=-1
        if self.y>H*TILE: self.alive=False
        self.anim+=1

    def draw(self,screen,cx):
        if not self.alive: return
        rx=int(self.x)-cx; ry=int(self.y)
        if self.kind=='mushroom':
            pygame.draw.rect(screen,MUSHROOM_C,(rx+2,ry+8,TILE-8,TILE-12))
            pygame.draw.ellipse(screen,MUSHROOM_C,(rx,ry,TILE-4,20))
            pygame.draw.circle(screen,WHITE,(rx+6,ry+6),4)
            pygame.draw.circle(screen,WHITE,(rx+22,ry+4),5)
        elif self.kind=='flower':
            pygame.draw.rect(screen,(0,180,0),(rx+14,ry+12,4,16))
            for i in range(5):
                a=i*(2*math.pi/5)
                pygame.draw.circle(screen,FLOWER_C,(rx+16+int(math.cos(a)*10),ry+10+int(math.sin(a)*10)),6)
            pygame.draw.circle(screen,WHITE,(rx+16,ry+10),5)
        else:  # star
            pts=[]
            for i in range(10):
                rr=12 if i%2==0 else 6; a=math.pi/2+i*(math.pi/5)
                pts.append((rx+16+int(math.cos(a)*rr),ry+16+int(math.sin(a)*rr)))
            if len(pts)>=3: pygame.draw.polygon(screen,STAR_C,pts)

# ──────────────────────────────────────────────────────────────
#  COIN ANIMATION
# ──────────────────────────────────────────────────────────────
class CoinAnim:
    def __init__(self,x,y):
        self.x=x+TILE//2-8; self.y=float(y); self.vy=-8.0; self.alive=True; self.t=0
    def update(self): self.vy+=0.6; self.y+=self.vy; self.t+=1; self.alive=self.t<40
    def draw(self,screen,cx): pygame.draw.ellipse(screen,COIN_YLW,(self.x-cx,int(self.y),16,20))

# ──────────────────────────────────────────────────────────────
#  PARTICLE
# ──────────────────────────────────────────────────────────────
class Particle:
    def __init__(self,x,y,col=RED_BRICK):
        self.x=float(x); self.y=float(y)
        self.vx=random.uniform(-4,4); self.vy=random.uniform(-8,-2)
        self.color=col; self.life=35
    def update(self): self.vy+=0.5; self.x+=self.vx; self.y+=self.vy; self.life-=1
    def draw(self,screen,cx):
        if self.life>0:
            r=max(1,self.life//8)
            pygame.draw.rect(screen,self.color,(int(self.x)-cx,int(self.y),r*2,r*2))

# ──────────────────────────────────────────────────────────────
#  ENEMY LOGIC
# ──────────────────────────────────────────────────────────────
def update_enemy(e,grid,player,particles,misc):
    H,W=len(grid),len(grid[0])
    t=e['type']
    if not e['alive']:
        if e['death_timer']>0: e['death_timer']-=1
        return
    e['anim']=(e.get('anim',0)+1)
    r=e['rect']

    if t=='firebar':
        e['angle']=(e['angle']+e['speed'])%360
        rad=math.radians(e['angle'])
        r.x=e['cx']+int(e['radius']*math.cos(rad))-8
        r.y=e['cy']+int(e['radius']*math.sin(rad))-8
        e['rect']=r; return

    if t=='bowser':
        e['vy']=e.get('vy',0)+GRAVITY*0.4
        if e['vy']>10: e['vy']=10
        r.x+=int(e['vx']*TILE/10); r.y+=int(e['vy'])
        if r.left<(W-55)*TILE: e['vx']=abs(e['vx'])
        if r.right>(W-4)*TILE:  e['vx']=-abs(e['vx'])
        rb=min(r.bottom//TILE,H-1); cm=min(r.centerx//TILE,W-1)
        if 0<=rb<H and 0<=cm<W and grid[rb][cm] in SOLID:
            r.bottom=rb*TILE; e['vy']=0
        e['fire_timer']=e.get('fire_timer',180)-1
        if e['fire_timer']<=0:
            e['fire_timer']=100+random.randint(0,40)
            dx=-3.0 if e['vx']<0 else 3.0
            misc.append({'kind':'bowser_flame','x':float(r.centerx),'y':float(r.centery),
                         'vx':dx,'vy':random.uniform(-2,2),'alive':True,'t':0})
        if r.top>H*TILE: e['alive']=False
        return

    vx=e['shell_vx'] if (t=='koopa' and e['shell']) else e['vx']
    e['vy']=e.get('vy',0)+GRAVITY*0.8
    if e['vy']>12: e['vy']=12
    r.x+=int(vx); r.y+=int(e['vy'])
    rb=min(r.bottom//TILE,H-1); cm=min(r.centerx//TILE,W-1)
    if 0<=rb<H and 0<=cm<W and grid[rb][cm] in SOLID:
        r.bottom=rb*TILE; e['vy']=0; e['on_ground']=True
    else: e['on_ground']=False
    ce=min((r.right//TILE if vx>0 else r.left//TILE),W-1); rm=min(r.centery//TILE,H-1)
    if 0<=ce<W and 0<=rm<H and grid[rm][ce] in SOLID:
        if t=='koopa' and e['shell']: e['shell_vx']*=-1
        else: e['vx']*=-1
    if t in ('goomba','koopa') and not(t=='koopa' and e['shell']) and vx!=0:
        ec=min((r.right//TILE if vx>0 else (r.left-1)//TILE),W-1)
        gr=min(r.bottom//TILE+1,H-1)
        if 0<=ec<W and 0<=gr<H and grid[gr][ec] not in SOLID: e['vx']*=-1
    if t=='hammerbro':
        e['throw_timer']=e.get('throw_timer',60)-1
        if e['throw_timer']<=0:
            e['throw_timer']=60+random.randint(0,30)
            dx2=3 if player.x>r.x else -3
            misc.append({'kind':'hammer','x':float(r.centerx),'y':float(r.top),
                         'vx':float(dx2),'vy':-6.0,'alive':True,'t':0})
    if r.top>H*TILE: e['alive']=False

def draw_enemy(screen,e,cx):
    t=e['type']
    if not e['alive']: return
    r=e['rect'].copy(); r.x-=cx
    if t=='goomba':
        pygame.draw.ellipse(screen,GOOMBA_C,(r.x,r.y,r.w,r.h))
        pygame.draw.ellipse(screen,(80,40,20),(r.x,r.y,r.w,r.h//2))
        pygame.draw.circle(screen,WHITE,(r.x+8,r.y+12),4)
        pygame.draw.circle(screen,WHITE,(r.x+r.w-8,r.y+12),4)
        pygame.draw.circle(screen,BLACK,(r.x+9,r.y+13),2)
        pygame.draw.circle(screen,BLACK,(r.x+r.w-7,r.y+13),2)
    elif t=='koopa':
        pygame.draw.rect(screen,(100,60,10) if e['shell'] else KOOPA_C,r)
        if not e['shell']: pygame.draw.ellipse(screen,(200,200,50),(r.x+2,r.y-8,r.w-4,12))
    elif t=='hammerbro':
        pygame.draw.rect(screen,KOOPA_C,r)
        pygame.draw.rect(screen,(200,200,50),(r.x+2,r.y-10,r.w-4,12))
        pygame.draw.rect(screen,HAMMER_C,(r.x-8,r.y-16,20,10))
    elif t=='bowser':
        pygame.draw.rect(screen,BOWSER_C,r)
        pygame.draw.circle(screen,(0,80,0),(r.x+r.w//2,r.y+12),14)
        pygame.draw.rect(screen,RED,(r.x+4,r.y+8,10,8))
        pygame.draw.rect(screen,RED,(r.x+r.w-14,r.y+8,10,8))
        for i in range(e['hp']): pygame.draw.rect(screen,(255,50,50),(r.x+i*8,r.y-10,6,6))
    elif t=='firebar':
        pygame.draw.circle(screen,FIRE_C,(r.x+8,r.y+8),8)
        pygame.draw.circle(screen,WHITE,(r.x+5,r.y+5),3)

def enemy_player_collide(player,enemies,particles,misc):
    if player.dead: return 0
    score=0
    for e in enemies:
        if not e.get('alive',False): continue
        t=e['type']
        if t=='firebar':
            if player.rect.colliderect(e['rect']): player.hit()
            continue
        if t=='bowser':
            if player.rect.colliderect(e['rect']): player.hit()
            continue
        if not player.rect.colliderect(e['rect']): continue
        if player.vy>1 and player.rect.bottom<=e['rect'].centery+12:
            if t=='koopa' and not e['shell']:
                e['shell']=True; e['shell_vx']=0; e['vx']=0; score+=100
            elif t=='koopa' and e['shell']:
                kd=1 if player.rect.centerx<e['rect'].centerx else -1
                e['shell_vx']=8*kd; play('kick')
            elif t=='hammerbro':
                e['alive']=False; e['death_timer']=20; score+=1000
                for _ in range(6): particles.append(Particle(e['rect'].centerx,e['rect'].centery,KOOPA_C))
            else:
                e['alive']=False; e['death_timer']=20; score+=100
                for _ in range(4): particles.append(Particle(e['rect'].centerx,e['rect'].centery,GOOMBA_C))
            player.vy=-10; play('stomp')
        else:
            if player.star_timer>0:
                if t=='bowser':
                    e['hp']-=1
                    if e['hp']<=0: e['alive']=False; e['death_timer']=30; score+=5000
                    play('bowser_hit')
                else:
                    e['alive']=False; e['death_timer']=20; score+=200
            else:
                player.hit()
    return score

# ──────────────────────────────────────────────────────────────
#  TILE RENDERER
# ──────────────────────────────────────────────────────────────
_fnt_sm = None
def draw_tiles(screen,grid,cx,lt):
    global _fnt_sm
    if _fnt_sm is None: _fnt_sm=pygame.font.SysFont(None,int(TILE*0.7))
    H,W=len(grid),len(grid[0])
    c0=max(0,cx//TILE-1); c1=min(W,cx//TILE+SW//TILE+2)
    for row in range(H):
        for col in range(c0,c1):
            tile=grid[row][col]; T=TILE
            if tile==AIR: continue
            rx=col*T-cx; ry=row*T
            if tile==GROUND:
                pygame.draw.rect(screen,BROWN,(rx,ry,T,T))
                pygame.draw.rect(screen,DARK_BRN,(rx,ry,T,T),2)
                pygame.draw.line(screen,DARK_BRN,(rx,ry+T//2),(rx+T,ry+T//2),1)
                pygame.draw.line(screen,DARK_BRN,(rx+T//2,ry),(rx+T//2,ry+T),1)
            elif tile==BRICK:
                pygame.draw.rect(screen,RED_BRICK,(rx,ry,T,T))
                pygame.draw.line(screen,(240,100,30),(rx,ry+T//2),(rx+T,ry+T//2),2)
                pygame.draw.line(screen,(240,100,30),(rx+T//2,ry),(rx+T//2,ry+T//2),2)
                pygame.draw.line(screen,(240,100,30),(rx+T//4,ry+T//2),(rx+T//4,ry+T),2)
                pygame.draw.line(screen,(240,100,30),(rx+3*T//4,ry+T//2),(rx+3*T//4,ry+T),2)
            elif tile in (QBLOCK,COIN_BLOCK,STAR_BLOCK):
                pygame.draw.rect(screen,QBLK_YLW,(rx,ry,T,T))
                pygame.draw.rect(screen,(200,140,0),(rx,ry,T,T),3)
                s=_fnt_sm.render('?',True,BLACK)
                screen.blit(s,(rx+T//2-s.get_width()//2,ry+T//2-s.get_height()//2))
            elif tile==USED:
                pygame.draw.rect(screen,USED_CLR,(rx,ry,T,T))
                pygame.draw.rect(screen,(100,70,30),(rx,ry,T,T),2)
            elif tile in (PIPE_TL,PIPE_BL):
                pygame.draw.rect(screen,PIP_GRN,(rx,ry,T,T))
                pygame.draw.rect(screen,PIP_DRK,(rx,ry,T,T),3)
                if tile==PIPE_TL:
                    pygame.draw.rect(screen,PIP_GRN,(rx-4,ry,T+4,T//2))
                    pygame.draw.rect(screen,PIP_DRK,(rx-4,ry,T+4,T//2),3)
            elif tile in (PIPE_TR,PIPE_BR):
                pygame.draw.rect(screen,PIP_GRN,(rx,ry,T,T))
                pygame.draw.rect(screen,PIP_DRK,(rx,ry,T,T),3)
                if tile==PIPE_TR:
                    pygame.draw.rect(screen,PIP_GRN,(rx,ry,T+4,T//2))
                    pygame.draw.rect(screen,PIP_DRK,(rx,ry,T+4,T//2),3)
            elif tile==PLATFORM:
                pygame.draw.rect(screen,BROWN,(rx,ry,T,T//2))
                pygame.draw.rect(screen,DARK_BRN,(rx,ry,T,T//2),2)
    if lt=='castle':
        tms=pygame.time.get_ticks()
        for col in range(c0,c1):
            if col<W and grid[H-1][col]==AIR:
                for row in range(H-2,H):
                    rx2=col*TILE-cx; ry2=row*TILE
                    lc=LAVA_CLR if (col+row+tms//200)%2==0 else (200,50,0)
                    pygame.draw.rect(screen,lc,(rx2,ry2,TILE,TILE))

# ──────────────────────────────────────────────────────────────
#  FLAGPOLE
# ──────────────────────────────────────────────────────────────
class Flagpole:
    def __init__(self,x,H):
        self.x=x; self.top_y=(H-12)*TILE; self.bot_y=(H-2)*TILE
        self.flag_y=self.top_y; self.sliding=False; self.done=False
        self.clear_t=0; self._bonus=0

    def check(self,player):
        pr=pygame.Rect(self.x,self.top_y,8,self.bot_y-self.top_y)
        if player.rect.colliderect(pr) and not self.sliding:
            self.sliding=True; player.vx=0
            ratio=1.0-max(0,min(1,(player.y-self.top_y)/(self.bot_y-self.top_y-32)))
            self._bonus=max(500,int(ratio*5000//500)*500)
            play('flagpole'); return self._bonus
        return 0

    def update(self,player):
        if self.sliding and not self.done:
            self.flag_y=min(self.flag_y+5,self.bot_y-20)
            player.x=self.x-player.w-2; player.y+=3
            if player.y>=self.bot_y-player.h:
                player.y=self.bot_y-player.h; self.done=True; self.clear_t=150; play('clear')

    def draw(self,screen,cx):
        rx=self.x-cx
        pygame.draw.rect(screen,(150,150,150),(rx,self.top_y,6,self.bot_y-self.top_y))
        pygame.draw.rect(screen,FLAG_C,(rx-24,self.flag_y,24,16))
        pygame.draw.circle(screen,(255,215,0),(rx+3,self.top_y),6)

# ──────────────────────────────────────────────────────────────
#  BACKGROUND DECORATIONS
# ──────────────────────────────────────────────────────────────
def draw_bg(screen,lt,cx):
    if lt=='overworld':
        for i in range(20):
            ox=(i*320-cx//3)%(SW+400)-200; oy=50+(i%3)*20
            pygame.draw.ellipse(screen,WHITE,(ox,oy,100,40))
            pygame.draw.ellipse(screen,WHITE,(ox+20,oy-15,70,35))
            pygame.draw.ellipse(screen,WHITE,(ox+50,oy-5,80,40))
        for i in range(12):
            hx=(i*420-cx//4)%(SW+600)-300
            pygame.draw.ellipse(screen,(80,180,60),(hx,SH-100-(i%2)*30,220,100))
    elif lt in ('castle','underground'):
        rng2=random.Random(42)
        for _ in range(60):
            pygame.draw.circle(screen,WHITE,(rng2.randint(0,SW),rng2.randint(0,SH-80)),1)
    elif lt=='underwater':
        tms=pygame.time.get_ticks()//100
        for i in range(15):
            bx=(i*57+tms*2)%SW; by=SH-(i*40+tms*3)%(SH-80)
            pygame.draw.circle(screen,(100,180,255),(bx,by),4,1)

# ──────────────────────────────────────────────────────────────
#  HUD + SCREENS
# ──────────────────────────────────────────────────────────────
def draw_hud(screen,world,lnum,score,coins,lives,timer,font):
    pygame.draw.rect(screen,BLACK,(0,0,SW,36))
    tc=WHITE if timer>100 else (255,80,80)
    txt=f"W{world}-{lnum}  SCORE:{score:07d}  COINS:{coins:02d}  x{lives}  TIME:{int(timer):03d}"
    screen.blit(font.render(txt,True,WHITE),(10,8))
    tip=font.render("N=skip  R=restart  B=world(title)  ESC=quit  X/Shift=run  Z/Ctrl=fire",True,(70,70,70))
    screen.blit(tip,(SW//2-tip.get_width()//2,SH-20))

def _center(screen,s,y): screen.blit(s,(SW//2-s.get_width()//2,y))

def draw_title(screen,big,font,wsel):
    screen.fill(BLACK)
    _center(screen,big.render("SUPER MARIO BROS",True,WHITE),130)
    for txt,col,y in [
        ("Enhanced Recreation  —  Worlds 1-1 through 8-4", QBLK_YLW, 210),
        ("Arrows/WASD=Move  Space=Jump  X/Shift=Run  Z/Ctrl=Fire", (180,180,180), 265),
        (f"World Select: {wsel+1}  (press B to change)", COIN_YLW, 315),
        ("Press ENTER or SPACE to start", WHITE, 390),
    ]:
        _center(screen,font.render(txt,True,col),y)

def draw_gameover(screen,big,font):
    screen.fill(BLACK)
    _center(screen,big.render("GAME OVER",True,WHITE),220)
    _center(screen,font.render("Press ENTER to return to title",True,(180,180,180)),330)

def draw_worldclear(screen,big,font,w):
    screen.fill(BLACK)
    _center(screen,big.render(f"WORLD {w} CLEAR!",True,QBLK_YLW),200)
    _center(screen,font.render("Press ENTER to continue",True,WHITE),310)

def draw_victory(screen,big,font):
    screen.fill(BLACK)
    _center(screen,big.render("YOU WIN!",True,QBLK_YLW),180)
    _center(screen,font.render("Congratulations! All 8 worlds completed!",True,WHITE),280)
    _center(screen,font.render("Press ENTER to play again",True,(180,180,180)),360)

# ──────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────
def main():
    screen=pygame.display.set_mode((SW,SH))
    pygame.display.set_caption("Super Mario Bros — Enhanced (1-1 to 8-4)")
    clock=pygame.time.Clock()
    font=pygame.font.SysFont(None,26); big=pygame.font.SysFont(None,60)

    STATE='title'; world=1; lnum=1
    score=0; coins=0; lives=3; world_sel=0

    grid=None; LW=0; player=None
    enemies=[]; particles=[]; coin_anims=[]; powerups=[]; fireballs=[]; misc=[]
    flagpole=None; cam=0; ltimer=400.0; bumped=[]

    # Optional: frame time monitor
    # frame_times = []

    def load(w,l):
        nonlocal grid,LW,player,enemies,particles,coin_anims
        nonlocal powerups,fireballs,misc,flagpole,cam,ltimer,bumped
        grid,LW=build_level(w,l)
        H=len(grid)
        player=Player(2*TILE,(H-4)*TILE)
        enemies=spawn_enemies(grid,w,l,LW)
        particles=[]; coin_anims=[]; powerups=[]; fireballs=[]; misc=[]
        flagpole=Flagpole((LW-4)*TILE,H)
        cam=0; ltimer=400.0; bumped=[]
        MUSIC.set(lt_music(LEVEL_TYPE[(w,l)]))

    running=True
    while running:
        dt=min(clock.tick(FPS)/1000.0, 1/30.0)
        MUSIC.update(dt)

        # Optional: monitor frame time
        # frame_times.append(clock.get_time())
        # if len(frame_times) > 60:
        #     avg = sum(frame_times) / len(frame_times)
        #     if avg > 1000/FPS + 1:
        #         print(f"Warning: average frame time {avg:.2f} ms")
        #     frame_times.clear()

        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: running=False
                if STATE=='title':
                    if ev.key==pygame.K_b: world_sel=(world_sel+1)%8
                    if ev.key in (pygame.K_RETURN,pygame.K_SPACE):
                        world=world_sel+1; lnum=1; score=0; coins=0; lives=3
                        load(world,lnum); STATE='play'
                elif STATE=='gameover' and ev.key==pygame.K_RETURN:
                    STATE='title'
                elif STATE=='worldclear' and ev.key==pygame.K_RETURN:
                    world+=1
                    if world>8: STATE='victory'
                    else: lnum=1; load(world,lnum); STATE='play'
                elif STATE=='victory' and ev.key==pygame.K_RETURN:
                    STATE='title'
                elif STATE=='play':
                    if ev.key==pygame.K_n:
                        lnum+=1
                        if lnum>4: lnum=1; world+=1
                        if world>8: STATE='victory'
                        else: load(world,lnum)
                    elif ev.key==pygame.K_r:
                        load(world,lnum)

        if STATE=='title':    draw_title(screen,big,font,world_sel); pygame.display.flip(); continue
        if STATE=='gameover': draw_gameover(screen,big,font);        pygame.display.flip(); continue
        if STATE=='worldclear':draw_worldclear(screen,big,font,world);pygame.display.flip(); continue
        if STATE=='victory':  draw_victory(screen,big,font);         pygame.display.flip(); continue

        # ── PLAY ──────────────────────────────────────────────
        lt=LEVEL_TYPE[(world,lnum)]
        keys=pygame.key.get_pressed()
        ltimer-=dt
        if ltimer<=0: player.kill()

        bumped.clear()
        player.update(keys,grid,bumped,fireballs)

        # Block bumps
        for bx,by in bumped:
            tile=grid[by][bx]
            if tile in (QBLOCK,COIN_BLOCK):
                grid[by][bx]=USED
                if tile==COIN_BLOCK:
                    coin_anims.append(CoinAnim(bx*TILE,by*TILE))
                    score+=200; coins+=1; play('coin')
                    if coins%100==0: lives+=1; play('1up')
                else:
                    kind='flower' if player.status>=1 else 'mushroom'
                    powerups.append(PowerUp(bx*TILE+2,(by-1)*TILE,kind)); play('coin')
            elif tile==STAR_BLOCK:
                grid[by][bx]=USED
                powerups.append(PowerUp(bx*TILE+2,(by-1)*TILE,'star')); play('coin')
            elif tile==BRICK:
                if player.big:
                    grid[by][bx]=AIR; play('brick')
                    for _ in range(6): particles.append(Particle(bx*TILE+TILE//2,by*TILE,RED_BRICK))
                    score+=50
                else: play('brick')

        for pu in powerups: pu.update(grid)
        for pu in powerups:
            if pu.alive and player.rect.colliderect(pu.rect):
                player.give(pu.kind); pu.alive=False
        powerups=[p for p in powerups if p.alive]

        for fb in fireballs: fb.update(grid)
        for fb in fireballs:
            if not fb.alive: continue
            for e in enemies:
                if not e.get('alive',False) or e['type']=='firebar': continue
                if fb.rect.colliderect(e['rect']):
                    if e['type']=='bowser':
                        e['hp']-=1
                        if e['hp']<=0: e['alive']=False; e['death_timer']=30; score+=5000
                        play('bowser_hit')
                    else:
                        e['alive']=False; e['death_timer']=20; score+=200
                        particles.append(Particle(e['rect'].centerx,e['rect'].centery))
                    fb.alive=False; break
        fireballs=[f for f in fireballs if f.alive]

        for m in misc:
            if not m['alive']: continue
            m['x']+=m['vx']; m['y']+=m['vy']
            if m['kind']=='hammer': m['vy']+=0.4
            m['t']+=1
            if m['t']>180 or m['x']<0 or m['x']>LW*TILE: m['alive']=False
            if player.rect.colliderect(pygame.Rect(int(m['x']),int(m['y']),12,12)):
                player.hit(); m['alive']=False
        misc=[m for m in misc if m['alive']]

        for c in coin_anims: c.update()
        coin_anims=[c for c in coin_anims if c.alive]

        for e in enemies: update_enemy(e,grid,player,particles,misc)
        score+=enemy_player_collide(player,enemies,particles,misc)

        if not flagpole.sliding and not player.dead:
            bonus=flagpole.check(player)
            if bonus: score+=bonus
        flagpole.update(player)

        for p in particles: p.update()
        particles=[p for p in particles if p.life>0]

        cam=max(0,min(int(player.x)-SW//2,LW*TILE-SW))

        if flagpole.done:
            flagpole.clear_t-=1
            if flagpole.clear_t<=0:
                score+=max(0,int(ltimer))*50
                lnum+=1
                if lnum>4:
                    STATE='worldclear' if world<8 else 'victory'
                else:
                    load(world,lnum)

        if player.dead and player.death_timer>90:
            lives-=1
            STATE='gameover' if lives<=0 else None
            if lives>0: load(world,lnum)

        # ── DRAW ──────────────────────────────────────────────
        screen.fill(lt_sky(lt))
        draw_bg(screen,lt,cam)
        draw_tiles(screen,grid,cam,lt)
        flagpole.draw(screen,cam)
        for pu in powerups: pu.draw(screen,cam)
        for c in coin_anims: c.draw(screen,cam)
        for m in misc:
            if not m['alive']: continue
            col=HAMMER_C if m['kind']=='hammer' else FIRE_C
            pygame.draw.rect(screen,col,(int(m['x'])-cam,int(m['y']),12,12))
        for fb in fireballs: fb.draw(screen,cam)
        for e in enemies: draw_enemy(screen,e,cam)
        for p in particles: p.draw(screen,cam)
        player.draw(screen,cam)
        draw_hud(screen,world,lnum,score,coins,lives,ltimer,font)
        pygame.display.flip()

    pygame.quit(); sys.exit()

if __name__=="__main__":
    main()
