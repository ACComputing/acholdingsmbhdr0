import pygame
import numpy as np
import sys
import random

# -------------------------
# Initialize
# -------------------------
pygame.mixer.pre_init(frequency=22050, size=-16, channels=1)
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=1)

# -------------------------
# Constants
# -------------------------
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
TILE_SIZE = 40
GRAVITY = 0.7
PLAYER_SPEED = 4
PLAYER_JUMP = -16
FPS = 60

# Tile IDs
AIR = 0
GROUND = 1
BRICK = 2
QUESTION = 3
PIPE_TOP_L = 4
PIPE_TOP_R = 5
PIPE_BODY_L = 6
PIPE_BODY_R = 7
COIN_BLOCK = 8   # question that gives coin
STAR_BLOCK = 9   # star hidden block
USED_BLOCK = 10

SOLID_TILES = {GROUND, BRICK, QUESTION, PIPE_TOP_L, PIPE_TOP_R, PIPE_BODY_L, PIPE_BODY_R, COIN_BLOCK, STAR_BLOCK, USED_BLOCK}

# Colors
SKY_BLUE    = (92,  148, 252)
NIGHT_SKY   = (0,   0,   0  )
UNDER_SKY   = (0,   0,   0  )
CAVE_SKY    = (0,   0,   0  )
SNOW_SKY    = (180, 210, 255)
WATER_SKY   = (20,  40,  120)
LAVA_SKY    = (10,  0,   0  )

GROUND_COLOR   = (227, 160, 20 )
BRICK_COLOR    = (200, 76,  12 )
QUESTION_COLOR = (252, 188, 20 )
USED_COLOR     = (150, 100, 50 )
PIPE_GREEN     = (0,   168, 0  )
PIPE_DARK      = (0,   100, 0  )
COIN_YELLOW    = (252, 188, 20 )
PLAYER_RED     = (220, 50,  0  )
GOOMBA_BROWN   = (160, 82,  45 )
KOOPA_GREEN    = (50,  160, 50 )
FIREBAR_COLOR  = (255, 100, 0  )
STAR_COLOR     = (255, 255, 0  )
MUSHROOM_RED   = (255, 0,   0  )
FLAG_COLOR     = (50,  200, 50 )
CASTLE_COLOR   = (100, 100, 100)
LAVA_COLOR     = (255, 80,  0  )
BLACK          = (0,   0,   0  )
WHITE          = (255, 255, 255)

# -------------------------
# Sound generation
# -------------------------
def gen_tone(freq, dur, vol=0.3, fade=True):
    sr = 22050
    n = int(dur * sr)
    t = np.linspace(0, dur, n, False)
    wave = np.sin(2 * np.pi * freq * t)
    if fade:
        env = np.linspace(1, 0, n)
        wave *= env
    arr = (wave * vol * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(arr)

def gen_sweep(f0, f1, dur, vol=0.3):
    sr = 22050
    n = int(dur * sr)
    t = np.linspace(0, dur, n, False)
    freq = np.linspace(f0, f1, n)
    wave = np.sin(2 * np.pi * np.cumsum(freq) / sr)
    env = np.linspace(1, 0, n)
    arr = (wave * env * vol * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(arr)

SND_JUMP     = gen_sweep(300, 600, 0.12)
SND_COIN     = gen_sweep(600, 900, 0.1)
SND_STOMP    = gen_sweep(200, 100, 0.1)
SND_POWERUP  = gen_sweep(400, 800, 0.3)
SND_DIE      = gen_sweep(600, 100, 0.5)
SND_FLAGPOLE = gen_sweep(300, 900, 0.6)
SND_CLEAR    = gen_tone(880, 0.4)

# -------------------------
# World themes
# -------------------------
WORLD_THEME = {
    1: 'overworld',
    2: 'overworld',
    3: 'overworld',
    4: 'castle',
    5: 'overworld',
    6: 'overworld',
    7: 'overworld',
    8: 'castle',
}

LEVEL_TYPE = {}  # (world, level) -> 'overworld'/'underground'/'castle'/'underwater'
for w in range(1, 9):
    for l in range(1, 5):
        if l == 4 or w in (4, 8):
            LEVEL_TYPE[(w, l)] = 'castle'
        elif l == 2 and w in (1, 3, 5, 7):
            LEVEL_TYPE[(w, l)] = 'underground'
        elif l == 3 and w in (2, 6):
            LEVEL_TYPE[(w, l)] = 'underwater'
        else:
            LEVEL_TYPE[(w, l)] = 'overworld'

def sky_color(ltype):
    if ltype == 'castle':      return LAVA_SKY
    if ltype == 'underground': return CAVE_SKY
    if ltype == 'underwater':  return WATER_SKY
    return SKY_BLUE

# -------------------------
# Level generation
# -------------------------
# Each level is a list of strings, 15 rows tall, variable width
# Tile chars: 0=air,1=ground,2=brick,3=question,4=pipe_tl,5=ptr,6=pbl,7=pbr,8=coin_q,F=flagpole area

def build_level(world, level_num):
    """Procedurally build a level resembling the original SMB1 structure."""
    ltype = LEVEL_TYPE[(world, level_num)]
    rng = random.Random(world * 100 + level_num)

    H = 15  # rows
    W = 60 + world * 5 + level_num * 2  # cols, gets longer in later worlds

    grid = [[0] * W for _ in range(H)]

    # Ground row (row 14) always filled except castles have lava gaps
    for x in range(W - 3):
        grid[H-1][x] = GROUND
        grid[H-2][x] = GROUND  # double ground base

    # Castle-specific: lava pit sections
    if ltype == 'castle':
        for _ in range(3 + world):
            gx = rng.randint(5, W - 15)
            gw = rng.randint(2, 4)
            for dx in range(gw):
                grid[H-1][gx+dx] = AIR
                grid[H-2][gx+dx] = AIR

    # Underground: ceiling
    if ltype == 'underground':
        for x in range(W - 3):
            grid[0][x] = GROUND
            grid[1][x] = GROUND

    # Gaps in overworld/underground
    if ltype in ('overworld', 'underground'):
        num_gaps = 2 + world + level_num // 2
        for _ in range(num_gaps):
            gx = rng.randint(10, W - 20)
            gw = rng.randint(2, 3 + world // 3)
            for dx in range(gw):
                cx = gx + dx
                if 0 <= cx < W - 4:
                    grid[H-1][cx] = AIR
                    grid[H-2][cx] = AIR

    # Platforms (bricks and question blocks)
    num_platforms = 4 + world + level_num
    for _ in range(num_platforms):
        px = rng.randint(5, W - 15)
        py = rng.choice([H-5, H-6, H-7, H-8])
        pw = rng.randint(2, 6)
        for dx in range(pw):
            cx = px + dx
            if 0 <= cx < W - 4 and grid[py][cx] == AIR:
                tile = rng.choice([BRICK, BRICK, BRICK, QUESTION, COIN_BLOCK])
                grid[py][cx] = tile

    # Pipes
    num_pipes = 2 + world
    placed_pipes = []
    for _ in range(num_pipes):
        attempts = 0
        while attempts < 20:
            px = rng.randint(8, W - 15)
            ph = rng.randint(2, 3)
            # Check ground clear
            ok = True
            for dx in range(2):
                if grid[H-1][px+dx] == AIR:
                    ok = False
            if not ok:
                attempts += 1
                continue
            # Too close to another pipe?
            too_close = any(abs(px - pp) < 5 for pp in placed_pipes)
            if too_close:
                attempts += 1
                continue
            placed_pipes.append(px)
            # Draw pipe
            for dy in range(ph):
                grid[H-2-dy][px]   = PIPE_BODY_L
                grid[H-2-dy][px+1] = PIPE_BODY_R
            grid[H-2-ph+1][px]   = PIPE_TOP_L
            grid[H-2-ph+1][px+1] = PIPE_TOP_R
            break

    # Staircase near end (world boss style)
    stair_x = W - 12
    for s in range(4):
        for dy in range(s + 1):
            gy = H - 2 - dy
            gx = stair_x + s
            if 0 <= gy < H and 0 <= gx < W:
                grid[gy][gx] = GROUND

    # Flag pole placeholder (last 3 cols)
    for y in range(H-2):
        grid[y][W-4] = 0  # flag pole is drawn separately

    # Clear player start area
    for y in range(H-2):
        grid[y][0] = AIR
        grid[y][1] = AIR
        grid[y][2] = AIR
    grid[H-1][0] = GROUND
    grid[H-1][1] = GROUND
    grid[H-1][2] = GROUND
    grid[H-2][0] = GROUND
    grid[H-2][1] = GROUND
    grid[H-2][2] = GROUND

    return grid, W

def spawn_enemies(grid, world, level_num, level_width):
    rng = random.Random(world * 1000 + level_num * 10 + 7)
    H = len(grid)
    enemies = []
    ltype = LEVEL_TYPE[(world, level_num)]

    num_goombas = 3 + world * 2 + level_num
    num_koopas  = world // 2 + level_num // 2

    placed = []
    for _ in range(num_goombas):
        for attempt in range(30):
            ex = rng.randint(8, level_width - 10)
            # Find ground
            ey = H - 3
            while ey > 0 and grid[ey][ex] == AIR:
                ey -= 1
            if grid[ey][ex] not in SOLID_TILES:
                continue
            if any(abs(ex - p) < 3 for p in placed):
                continue
            placed.append(ex)
            enemies.append({'type': 'goomba', 'rect': pygame.Rect(ex * TILE_SIZE, ey * TILE_SIZE - TILE_SIZE + 5, TILE_SIZE - 5, TILE_SIZE - 5),
                            'vx': -1, 'alive': True, 'death_timer': 0})
            break

    for _ in range(num_koopas):
        for attempt in range(30):
            ex = rng.randint(10, level_width - 10)
            ey = H - 3
            while ey > 0 and grid[ey][ex] == AIR:
                ey -= 1
            if grid[ey][ex] not in SOLID_TILES:
                continue
            if any(abs(ex - p) < 4 for p in placed):
                continue
            placed.append(ex)
            enemies.append({'type': 'koopa', 'rect': pygame.Rect(ex * TILE_SIZE, ey * TILE_SIZE - TILE_SIZE + 5, TILE_SIZE - 5, TILE_SIZE - 5),
                            'vx': -1, 'alive': True, 'shell': False, 'shell_vx': 0, 'death_timer': 0})
            break

    # Firebars in castles
    if ltype == 'castle':
        for i in range(2 + world // 2):
            fx = rng.randint(10, level_width - 15) * TILE_SIZE
            fy = rng.randint(3, 10) * TILE_SIZE
            enemies.append({'type': 'firebar', 'cx': fx, 'cy': fy, 'angle': 0,
                            'radius': (2 + i % 3) * TILE_SIZE, 'speed': 2 + world * 0.3,
                            'alive': True, 'death_timer': 0})

    return enemies

# -------------------------
# Player
# -------------------------
class Player:
    def __init__(self, x, y):
        self.reset(x, y)

    def reset(self, x, y):
        self.rect = pygame.Rect(x, y, TILE_SIZE - 6, TILE_SIZE - 6)
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.facing = 1
        self.big = False
        self.invincible = 0  # frames
        self.dead = False
        self.death_timer = 0

    def collide_tiles(self, dx, dy, grid):
        H, W = len(grid), len(grid[0])
        self.rect.x += dx
        self.rect.y += dy
        for row in range(max(0, self.rect.top // TILE_SIZE), min(H, self.rect.bottom // TILE_SIZE + 1)):
            for col in range(max(0, self.rect.left // TILE_SIZE), min(W, self.rect.right // TILE_SIZE + 1)):
                if grid[row][col] in SOLID_TILES:
                    block = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if self.rect.colliderect(block):
                        if dx > 0: self.rect.right = block.left
                        if dx < 0: self.rect.left  = block.right
                        if dy > 0:
                            self.rect.bottom = block.top
                            self.vy = 0
                        if dy < 0:
                            self.rect.top = block.bottom
                            self.vy = 0
                            # Bump block
                            return (col, row)
        return None

    def check_ground(self, grid):
        H, W = len(grid), len(grid[0])
        test = self.rect.copy()
        test.y += 2
        for row in range(max(0, test.top // TILE_SIZE), min(H, test.bottom // TILE_SIZE + 1)):
            for col in range(max(0, test.left // TILE_SIZE), min(W, test.right // TILE_SIZE + 1)):
                if grid[row][col] in SOLID_TILES:
                    block = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if test.colliderect(block):
                        return True
        return False

    def update(self, keys, grid, bumped_blocks):
        if self.dead:
            self.death_timer += 1
            self.vy += GRAVITY * 0.5
            self.rect.y += int(self.vy)
            return

        if self.invincible > 0:
            self.invincible -= 1

        self.vx = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.vx = -PLAYER_SPEED; self.facing = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.vx =  PLAYER_SPEED;  self.facing =  1
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vy = PLAYER_JUMP
            self.on_ground = False
            SND_JUMP.play()

        self.vy += GRAVITY
        if self.vy > 20: self.vy = 20

        bumped = None
        if self.vx != 0:
            self.collide_tiles(int(self.vx), 0, grid)
        if self.vy != 0:
            bumped = self.collide_tiles(0, int(self.vy), grid)
            if bumped and self.vy < 0:
                bumped_blocks.append(bumped)

        self.on_ground = self.check_ground(grid)

        H = len(grid)
        if self.rect.top > H * TILE_SIZE:
            self.kill()

    def kill(self):
        if self.invincible > 0 or self.dead:
            return
        self.dead = True
        self.vy = -12
        SND_DIE.play()

    def draw(self, screen, camera_x):
        if self.dead and self.death_timer % 4 < 2:
            return
        if self.invincible > 0 and self.invincible % 6 < 3:
            return
        rx = self.rect.x - camera_x
        ry = self.rect.y
        color = PLAYER_RED
        pygame.draw.rect(screen, color, (rx, ry, self.rect.width, self.rect.height))
        # Eyes
        ex = rx + (self.rect.width - 8) if self.facing > 0 else rx + 2
        pygame.draw.rect(screen, WHITE, (ex, ry + 4, 8, 6))
        pygame.draw.rect(screen, BLACK, (ex + (4 if self.facing > 0 else 0), ry + 5, 4, 4))
        # Hat
        pygame.draw.rect(screen, (150, 30, 0), (rx, ry - 6, self.rect.width, 7))

# -------------------------
# Enemy update/draw helpers
# -------------------------
def update_enemy(e, grid):
    H, W = len(grid), len(grid[0])
    t = e['type']

    if t in ('goomba', 'koopa'):
        if e['death_timer'] > 0:
            e['death_timer'] -= 1
            return
        if not e['alive']:
            return
        r = e['rect']

        if t == 'koopa' and e['shell']:
            vx = e['shell_vx']
        else:
            vx = e['vx']

        r.x += vx

        # Wall bounce
        col_l = r.left // TILE_SIZE
        col_r = r.right // TILE_SIZE
        row_m = (r.centery) // TILE_SIZE
        if 0 <= col_l < W and 0 <= row_m < H and grid[row_m][col_l] in SOLID_TILES:
            r.left = (col_l + 1) * TILE_SIZE
            if t == 'koopa' and e['shell']:
                e['shell_vx'] *= -1
            else:
                e['vx'] *= -1
        if 0 <= col_r < W and 0 <= row_m < H and grid[row_m][col_r] in SOLID_TILES:
            r.right = col_r * TILE_SIZE
            if t == 'koopa' and e['shell']:
                e['shell_vx'] *= -1
            else:
                e['vx'] *= -1

        # Edge turning (goombas)
        if t == 'goomba':
            r.y += 2
            edge_col = (r.right // TILE_SIZE if vx > 0 else r.left // TILE_SIZE)
            edge_row = r.bottom // TILE_SIZE
            if 0 <= edge_col < W and 0 <= edge_row < H:
                if grid[edge_row][edge_col] not in SOLID_TILES:
                    e['vx'] *= -1
            r.y -= 2

        # Fall off map
        if r.top > H * TILE_SIZE:
            e['alive'] = False

    elif t == 'firebar':
        import math
        e['angle'] = (e['angle'] + e['speed']) % 360
        rad = math.radians(e['angle'])
        e['rect'] = pygame.Rect(
            e['cx'] + int(e['radius'] * math.cos(rad)) - 8,
            e['cy'] + int(e['radius'] * math.sin(rad)) - 8,
            16, 16)

def draw_enemy(screen, e, camera_x):
    t = e['type']
    if t in ('goomba', 'koopa'):
        if not e['alive']:
            return
        r = e['rect'].copy()
        r.x -= camera_x
        if t == 'goomba':
            pygame.draw.rect(screen, GOOMBA_BROWN, r)
            pygame.draw.ellipse(screen, (80, 40, 20), (r.x, r.y, r.width, r.height // 2))
            pygame.draw.circle(screen, WHITE, (r.x + 8, r.y + 12), 4)
            pygame.draw.circle(screen, WHITE, (r.x + r.width - 8, r.y + 12), 4)
        else:
            color = (100, 50, 0) if e['shell'] else KOOPA_GREEN
            pygame.draw.rect(screen, color, r)
            if not e['shell']:
                pygame.draw.ellipse(screen, (200, 200, 50), (r.x + 2, r.y - 8, r.width - 4, 12))
    elif t == 'firebar':
        import math
        r = e['rect'].copy()
        r.x -= camera_x
        pygame.draw.circle(screen, FIREBAR_COLOR, r.center, 8)
        # Draw connecting arm
        cx = e['cx'] - camera_x
        cy = e['cy']
        pygame.draw.line(screen, (255, 150, 0), (cx, cy), r.center, 3)

def player_enemy_collision(player, enemies):
    if player.dead or player.invincible > 0:
        return
    for e in enemies:
        if not e.get('alive', False):
            continue
        t = e['type']
        if t == 'firebar':
            if player.rect.colliderect(e['rect']):
                if player.big:
                    player.big = False
                    player.invincible = 90
                else:
                    player.kill()
            continue
        if player.rect.colliderect(e['rect']):
            # Stomp?
            if player.vy > 0 and player.rect.bottom <= e['rect'].centery + 10:
                if t == 'koopa' and not e['shell']:
                    e['shell'] = True
                    e['shell_vx'] = 0
                    e['vx'] = 0
                elif t == 'koopa' and e['shell']:
                    e['shell_vx'] = 6 if player.rect.centerx < e['rect'].centerx else -6
                else:
                    e['alive'] = False
                    e['death_timer'] = 30
                player.vy = -10
                SND_STOMP.play()
            else:
                if player.big:
                    player.big = False
                    player.invincible = 90
                else:
                    player.kill()

# -------------------------
# Coins / collectibles
# -------------------------
class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x + 10, y + 5, 20, 30)
        self.alive = True
        self.anim = 0

    def draw(self, screen, camera_x):
        if not self.alive:
            return
        self.anim += 1
        rx = self.rect.x - camera_x
        pygame.draw.ellipse(screen, COIN_YELLOW, (rx, self.rect.y, 20, 30))

# -------------------------
# Particles
# -------------------------
class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-8, -2)
        self.color = color
        self.life = 30

    def update(self):
        self.vy += 0.5
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, screen, camera_x):
        if self.life > 0:
            pygame.draw.circle(screen, self.color, (int(self.x - camera_x), int(self.y)), max(1, self.life // 10))

# -------------------------
# Flagpole / level end
# -------------------------
class Flagpole:
    def __init__(self, x, height):
        self.x = x
        self.top_y = (height - 12) * TILE_SIZE
        self.bottom_y = (height - 2) * TILE_SIZE
        self.flag_y = self.top_y
        self.sliding = False
        self.done = False
        self.clear_timer = 0

    def check(self, player):
        pole_rect = pygame.Rect(self.x, self.top_y, 8, self.bottom_y - self.top_y)
        if player.rect.colliderect(pole_rect) and not self.sliding:
            self.sliding = True
            player.vx = 0
            SND_FLAGPOLE.play()

    def update(self, player):
        if self.sliding and not self.done:
            self.flag_y = min(self.flag_y + 4, self.bottom_y - 20)
            player.rect.x = self.x - player.rect.width
            player.rect.y += 3
            if player.rect.y >= self.bottom_y - player.rect.height:
                player.rect.y = self.bottom_y - player.rect.height
                self.done = True
                self.clear_timer = 120
                SND_CLEAR.play()

    def draw(self, screen, camera_x):
        rx = self.x - camera_x
        pygame.draw.rect(screen, (150, 150, 150), (rx, self.top_y, 6, self.bottom_y - self.top_y))
        pygame.draw.rect(screen, FLAG_COLOR, (rx - 24, self.flag_y, 24, 16))
        pygame.draw.circle(screen, (255, 215, 0), (rx + 3, self.top_y), 6)

# -------------------------
# Draw level tiles
# -------------------------
def draw_tiles(screen, grid, camera_x, ltype):
    H, W = len(grid), len(grid[0])
    cam_col_start = max(0, camera_x // TILE_SIZE - 1)
    cam_col_end   = min(W, camera_x // TILE_SIZE + SCREEN_WIDTH // TILE_SIZE + 2)
    for row in range(H):
        for col in range(cam_col_start, cam_col_end):
            tile = grid[row][col]
            if tile == AIR:
                continue
            rx = col * TILE_SIZE - camera_x
            ry = row * TILE_SIZE
            if tile == GROUND:
                pygame.draw.rect(screen, GROUND_COLOR, (rx, ry, TILE_SIZE, TILE_SIZE))
                pygame.draw.rect(screen, (180, 120, 0), (rx, ry, TILE_SIZE, TILE_SIZE), 2)
            elif tile == BRICK:
                pygame.draw.rect(screen, BRICK_COLOR, (rx, ry, TILE_SIZE, TILE_SIZE))
                pygame.draw.line(screen, (240, 100, 30), (rx, ry + TILE_SIZE // 2), (rx + TILE_SIZE, ry + TILE_SIZE // 2), 2)
                pygame.draw.line(screen, (240, 100, 30), (rx + TILE_SIZE // 2, ry), (rx + TILE_SIZE // 2, ry + TILE_SIZE // 2), 2)
                pygame.draw.line(screen, (240, 100, 30), (rx + TILE_SIZE // 4, ry + TILE_SIZE // 2), (rx + TILE_SIZE // 4, ry + TILE_SIZE), 2)
                pygame.draw.line(screen, (240, 100, 30), (rx + 3 * TILE_SIZE // 4, ry + TILE_SIZE // 2), (rx + 3 * TILE_SIZE // 4, ry + TILE_SIZE), 2)
            elif tile in (QUESTION, COIN_BLOCK):
                pygame.draw.rect(screen, QUESTION_COLOR, (rx, ry, TILE_SIZE, TILE_SIZE))
                pygame.draw.rect(screen, (200, 140, 0), (rx, ry, TILE_SIZE, TILE_SIZE), 3)
                font_sm = pygame.font.SysFont(None, 28)
                s = font_sm.render('?', True, BLACK)
                screen.blit(s, (rx + TILE_SIZE // 2 - s.get_width() // 2, ry + TILE_SIZE // 2 - s.get_height() // 2))
            elif tile == USED_BLOCK:
                pygame.draw.rect(screen, USED_COLOR, (rx, ry, TILE_SIZE, TILE_SIZE))
                pygame.draw.rect(screen, (100, 70, 30), (rx, ry, TILE_SIZE, TILE_SIZE), 2)
            elif tile in (PIPE_TOP_L, PIPE_BODY_L):
                pygame.draw.rect(screen, PIPE_GREEN, (rx, ry, TILE_SIZE, TILE_SIZE))
                pygame.draw.rect(screen, PIPE_DARK, (rx, ry, TILE_SIZE, TILE_SIZE), 3)
                if tile == PIPE_TOP_L:
                    pygame.draw.rect(screen, PIPE_GREEN, (rx - 4, ry, TILE_SIZE + 4, TILE_SIZE // 2))
                    pygame.draw.rect(screen, PIPE_DARK, (rx - 4, ry, TILE_SIZE + 4, TILE_SIZE // 2), 3)
            elif tile in (PIPE_TOP_R, PIPE_BODY_R):
                pygame.draw.rect(screen, PIPE_GREEN, (rx, ry, TILE_SIZE, TILE_SIZE))
                pygame.draw.rect(screen, PIPE_DARK, (rx, ry, TILE_SIZE, TILE_SIZE), 3)

    # Lava in castles
    if ltype == 'castle':
        for col in range(cam_col_start, cam_col_end):
            if grid[H-1][col] == AIR:
                for row in range(H-2, H):
                    rx = col * TILE_SIZE - camera_x
                    ry = row * TILE_SIZE
                    c = LAVA_COLOR if (col + row + pygame.time.get_ticks() // 200) % 2 == 0 else (200, 50, 0)
                    pygame.draw.rect(screen, c, (rx, ry, TILE_SIZE, TILE_SIZE))

# -------------------------
# HUD
# -------------------------
def draw_hud(screen, world, level_num, score, coins, lives, font):
    pygame.draw.rect(screen, (0, 0, 0, 120), (0, 0, SCREEN_WIDTH, 36))
    s = font.render(f"WORLD {world}-{level_num}   SCORE:{score:06d}   COINS:{coins:02d}   LIVES:{lives}", True, WHITE)
    screen.blit(s, (10, 8))

# -------------------------
# Screens
# -------------------------
def title_screen(screen, font, big_font):
    screen.fill(BLACK)
    t = big_font.render("SUPER MARIO BROS", True, WHITE)
    screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 150))
    s = font.render("Worlds 1-1 through 8-4", True, QUESTION_COLOR)
    screen.blit(s, (SCREEN_WIDTH // 2 - s.get_width() // 2, 240))
    p = font.render("Arrow Keys / WASD to move, SPACE/W to jump", True, (180, 180, 180))
    screen.blit(p, (SCREEN_WIDTH // 2 - p.get_width() // 2, 310))
    st = font.render("Press ENTER or SPACE to start", True, WHITE)
    screen.blit(st, (SCREEN_WIDTH // 2 - st.get_width() // 2, 400))

def game_over_screen(screen, font, big_font):
    screen.fill(BLACK)
    t = big_font.render("GAME OVER", True, WHITE)
    screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 220))
    s = font.render("Press ENTER to play again", True, (180, 180, 180))
    screen.blit(s, (SCREEN_WIDTH // 2 - s.get_width() // 2, 330))

def world_clear_screen(screen, font, big_font, world):
    screen.fill(BLACK)
    t = big_font.render(f"WORLD {world} CLEAR!", True, QUESTION_COLOR)
    screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 200))
    s = font.render("Press ENTER to continue", True, WHITE)
    screen.blit(s, (SCREEN_WIDTH // 2 - s.get_width() // 2, 310))

def victory_screen(screen, font, big_font):
    screen.fill(BLACK)
    t = big_font.render("YOU WIN!", True, QUESTION_COLOR)
    screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 180))
    s = font.render("Congratulations! You completed all 8 worlds!", True, WHITE)
    screen.blit(s, (SCREEN_WIDTH // 2 - s.get_width() // 2, 280))
    p = font.render("Press ENTER to play again", True, (180, 180, 180))
    screen.blit(p, (SCREEN_WIDTH // 2 - p.get_width() // 2, 360))

# -------------------------
# Main
# -------------------------
def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Super Mario Bros 1-1 to 8-4")
    clock = pygame.time.Clock()
    font     = pygame.font.SysFont(None, 28)
    big_font = pygame.font.SysFont(None, 64)

    STATE = 'title'
    world, level_num = 1, 1
    score, coins, lives = 0, 0, 3

    grid, level_width = None, 0
    player = None
    enemies, particles, coin_objects = [], [], []
    flagpole = None
    camera_x = 0
    level_timer = 0
    bumped_blocks = []

    def load_level(w, l):
        nonlocal grid, level_width, player, enemies, particles, coin_objects, flagpole, camera_x, level_timer, bumped_blocks
        grid, level_width = build_level(w, l)
        H = len(grid)
        # Find player start (ground at left)
        sy = (H - 3) * TILE_SIZE
        player = Player(2 * TILE_SIZE, sy)
        enemies = spawn_enemies(grid, w, l, level_width)
        particles = []
        coin_objects = []
        flagpole = Flagpole((level_width - 4) * TILE_SIZE, H)
        camera_x = 0
        level_timer = 400
        bumped_blocks = []

    running = True
    transition_timer = 0

    while running:
        clock.tick(FPS)
        dt = 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if STATE == 'title' and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    world, level_num = 1, 1
                    score, coins, lives = 0, 0, 3
                    load_level(world, level_num)
                    STATE = 'play'
                elif STATE == 'gameover' and event.key == pygame.K_RETURN:
                    STATE = 'title'
                elif STATE == 'worldclear' and event.key == pygame.K_RETURN:
                    world += 1
                    if world > 8:
                        STATE = 'victory'
                    else:
                        level_num = 1
                        load_level(world, level_num)
                        STATE = 'play'
                elif STATE == 'victory' and event.key == pygame.K_RETURN:
                    STATE = 'title'
                # Debug: skip level
                elif STATE == 'play' and event.key == pygame.K_n:
                    level_num += 1
                    if level_num > 4:
                        level_num = 1
                        world += 1
                    if world > 8:
                        STATE = 'victory'
                    else:
                        load_level(world, level_num)

        # --- Draw ---
        if STATE == 'title':
            title_screen(screen, font, big_font)
            pygame.display.flip()
            continue

        if STATE == 'gameover':
            game_over_screen(screen, font, big_font)
            pygame.display.flip()
            continue

        if STATE == 'worldclear':
            world_clear_screen(screen, font, big_font, world)
            pygame.display.flip()
            continue

        if STATE == 'victory':
            victory_screen(screen, font, big_font)
            pygame.display.flip()
            continue

        # --- PLAY ---
        ltype = LEVEL_TYPE[(world, level_num)]
        keys = pygame.key.get_pressed()

        # Timer
        level_timer -= 1 / FPS
        if level_timer <= 0:
            player.kill()

        # Update player
        bumped_blocks.clear()
        player.update(keys, grid, bumped_blocks)

        # Bumped blocks
        for (bx, by) in bumped_blocks:
            tile = grid[by][bx]
            if tile in (QUESTION, COIN_BLOCK):
                grid[by][bx] = USED_BLOCK
                coin_objects.append(Coin(bx * TILE_SIZE, (by - 1) * TILE_SIZE))
                score += 200
                coins += 1
                SND_COIN.play()
            elif tile == BRICK:
                if player.big:
                    grid[by][bx] = AIR
                    for _ in range(6):
                        particles.append(Particle(bx * TILE_SIZE + TILE_SIZE // 2, by * TILE_SIZE, BRICK_COLOR))
                    score += 50

        # Update coins
        for c in coin_objects:
            c.anim += 1
            if c.anim > 30:
                c.alive = False
        coin_objects = [c for c in coin_objects if c.alive]

        # Update enemies
        for e in enemies:
            update_enemy(e, grid)

        # Player-enemy collision
        player_enemy_collision(player, enemies)

        # Kill enemies that fell
        for e in enemies:
            if e['type'] in ('goomba', 'koopa') and e['alive']:
                if e['rect'].top > len(grid) * TILE_SIZE:
                    e['alive'] = False

        # Flagpole
        if not flagpole.sliding and not player.dead:
            flagpole.check(player)
        flagpole.update(player)

        # Particles
        for p in particles:
            p.update()
        particles = [p for p in particles if p.life > 0]

        # Camera
        target_x = player.rect.centerx - SCREEN_WIDTH // 2
        camera_x = max(0, min(target_x, level_width * TILE_SIZE - SCREEN_WIDTH))

        # Level complete
        if flagpole.done:
            flagpole.clear_timer -= 1
            if flagpole.clear_timer <= 0:
                score += max(0, int(level_timer)) * 50
                level_num += 1
                if level_num > 4:
                    if world == 8:
                        STATE = 'victory'
                    else:
                        STATE = 'worldclear'
                else:
                    load_level(world, level_num)

        # Player death
        if player.dead and player.death_timer > 90:
            lives -= 1
            if lives <= 0:
                STATE = 'gameover'
            else:
                load_level(world, level_num)

        # ---- DRAW ----
        screen.fill(sky_color(ltype))

        # Hills / clouds decoration (overworld)
        if ltype == 'overworld':
            for hx in range(-1, level_width // 5 + 1):
                base = (hx * 5 * TILE_SIZE - camera_x % (5 * TILE_SIZE)) + hx * 100
                # Cloud
                cx = (hx * 7 * TILE_SIZE - camera_x // 2) % (SCREEN_WIDTH + 200) - 100
                pygame.draw.ellipse(screen, WHITE, (cx, 60, 100, 40))
                pygame.draw.ellipse(screen, WHITE, (cx + 20, 40, 70, 40))
                pygame.draw.ellipse(screen, WHITE, (cx + 50, 50, 80, 40))
            # Hills
            for hx in range(-1, level_width // 4 + 1):
                hcx = (hx * 4 * TILE_SIZE - camera_x // 3) % (SCREEN_WIDTH + 200) - 100
                pygame.draw.ellipse(screen, (80, 180, 60), (hcx, SCREEN_HEIGHT - 130, 180, 100))

        # Stars in night/castle
        if ltype in ('castle', 'underground'):
            rng2 = random.Random(42)
            for _ in range(50):
                sx = rng2.randint(0, SCREEN_WIDTH)
                sy = rng2.randint(0, SCREEN_HEIGHT - 100)
                pygame.draw.circle(screen, WHITE, (sx, sy), 1)

        draw_tiles(screen, grid, camera_x, ltype)
        flagpole.draw(screen, camera_x)

        for c in coin_objects:
            c.draw(screen, camera_x)

        for e in enemies:
            draw_enemy(screen, e, camera_x)

        for p in particles:
            p.draw(screen, camera_x)

        player.draw(screen, camera_x)
        draw_hud(screen, world, level_num, score, coins, lives, font)

        # Timer display
        tsec = int(level_timer)
        tc = WHITE if tsec > 100 else (255, 80, 80)
        ts = font.render(f"TIME {tsec:03d}", True, tc)
        screen.blit(ts, (SCREEN_WIDTH - 120, 8))

        # Tip
        tip = font.render("N=skip level  ESC=quit", True, (100, 100, 100))
        screen.blit(tip, (SCREEN_WIDTH // 2 - tip.get_width() // 2, SCREEN_HEIGHT - 22))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
