import pygame
import numpy as np

# -------------------------
# Initialize Pygame
# -------------------------
# FIX: Initialize mixer BEFORE pygame.init() to enforce mono settings.
# pygame.init() initializes the mixer with default stereo settings,
# and subsequent mixer.init() calls are ignored.
pygame.mixer.init(frequency=22050, size=-16, channels=1)  # mono
pygame.init()

# -------------------------
# Constants
# -------------------------
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
TILE_SIZE = 40
GRAVITY = 0.8
PLAYER_SPEED = 5
PLAYER_JUMP = -15
FPS = 60

# Colors
SKY_BLUE = (135, 206, 235)
GROUND_BROWN = (139, 69, 19)
BRICK_RED = (200, 50, 50)
QUESTION_YELLOW = (255, 255, 0)
PLAYER_COLOR = (255, 0, 0)
GOOMBA_COLOR = (100, 50, 50)

# -------------------------
# Jump Sound (Fixed)
# -------------------------
def create_jump_sound():
    sample_rate = 22050
    duration = 0.1
    frequency = 440
    frames = int(duration * sample_rate)
    # 1D array for mono mixer
    arr = np.zeros(frames, dtype=np.int16)
    for i in range(frames):
        t = i / sample_rate
        arr[i] = int(32767 * 0.3 * np.sin(2 * np.pi * frequency * t))
    return pygame.sndarray.make_sound(arr)

jump_sound = create_jump_sound()

# -------------------------
# Level Layout (1-1 simplified)
# -------------------------
level_map = [
    "00000000000000000000",
    "00000000000000000000",
    "00000000000000000000",
    "00000000000000000000",
    "00000000000000000000",
    "00000000000000000000",
    "00000000000000000000",
    "00000000000000000000",
    "00000000000000000000",
    "00000000000000000000",
    "00000111000000000000",  # small platform
    "00000000000000000000",
    "00000000000000000000",
    "00000000000000000000",
    "11111111111111111111",
]
level = [[int(c) for c in row] for row in level_map]

# Player start
player_start_x = 2 * TILE_SIZE
player_start_y = 12 * TILE_SIZE

# -------------------------
# Player Class
# -------------------------
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, TILE_SIZE-5, TILE_SIZE-5)
        self.vx = 0
        self.vy = 0
        self.on_ground = False

    def move(self, dx, dy):
        if dx != 0:
            self.move_single_axis(dx, 0)
        if dy != 0:
            self.move_single_axis(0, dy)

    def move_single_axis(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy
        for y in range(max(0, self.rect.top // TILE_SIZE), min(len(level), (self.rect.bottom + TILE_SIZE - 1) // TILE_SIZE)):
            for x in range(max(0, self.rect.left // TILE_SIZE), min(len(level[0]), (self.rect.right + TILE_SIZE - 1) // TILE_SIZE)):
                if level[y][x] in (1, 2, 3):
                    block = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if self.rect.colliderect(block):
                        if dx > 0:
                            self.rect.right = block.left
                        if dx < 0:
                            self.rect.left = block.right
                        if dy > 0:
                            self.rect.bottom = block.top
                            self.vy = 0
                            # self.on_ground = True   # Removed - will be set by ground check
                        if dy < 0:
                            self.rect.top = block.bottom
                            self.vy = 0

    def check_ground(self):
        """Check if there is a solid tile directly below the player."""
        test_rect = self.rect.copy()
        test_rect.y += 1  # Slightly below feet
        # Check tiles that could intersect
        for y in range(max(0, test_rect.top // TILE_SIZE), min(len(level), (test_rect.bottom + TILE_SIZE - 1) // TILE_SIZE)):
            for x in range(max(0, test_rect.left // TILE_SIZE), min(len(level[0]), (test_rect.right + TILE_SIZE - 1) // TILE_SIZE)):
                if level[y][x] in (1, 2, 3):
                    block = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if test_rect.colliderect(block):
                        return True
        return False

    def update(self, keys):
        self.vx = 0
        if keys[pygame.K_LEFT]:
            self.vx = -PLAYER_SPEED
        if keys[pygame.K_RIGHT]:
            self.vx = PLAYER_SPEED
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vy = PLAYER_JUMP
            self.on_ground = False
            jump_sound.play()
        self.vy += GRAVITY
        if self.vy > 15:
            self.vy = 15
        self.move(self.vx, self.vy)

        # Update ground state after movement
        self.on_ground = self.check_ground()

        # Fall off bottom -> respawn
        if self.rect.top > len(level) * TILE_SIZE:
            self.rect.x, self.rect.y = player_start_x, player_start_y
            self.vy = 0

# -------------------------
# Goomba Class
# -------------------------
class Goomba:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, TILE_SIZE-5, TILE_SIZE-5)
        self.vx = -1
        self.alive = True

    def update(self):
        if not self.alive:
            return
        self.rect.x += self.vx

        # Check for turning at edges (original logic, but with bounds check)
        below = self.rect.bottom // TILE_SIZE
        left_tile = self.rect.left // TILE_SIZE
        right_tile = self.rect.right // TILE_SIZE

        # Only check if below is within level height
        if below < len(level):
            # Check bounds for left and right tiles
            left_valid = 0 <= left_tile < len(level[0])
            right_valid = 0 <= right_tile < len(level[0])

            # Consider a tile solid if it's within bounds and is a ground/brick/question block
            left_solid = left_valid and level[below][left_tile] in (1, 2, 3)
            right_solid = right_valid and level[below][right_tile] in (1, 2, 3)

            # If both sides have no ground below, turn around
            if not left_solid and not right_solid:
                self.vx *= -1

    def draw(self, screen, camera_x):
        if self.alive:
            rect = self.rect.copy()
            rect.x -= camera_x
            pygame.draw.rect(screen, GOOMBA_COLOR, rect)

# -------------------------
# Main Loop
# -------------------------
def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Super Mario 1-1 Simplified")
    clock = pygame.time.Clock()
    player = Player(player_start_x, player_start_y)
    goombas = [Goomba(8 * TILE_SIZE, 11 * TILE_SIZE)]
    camera_x = 0
    running = True
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        keys = pygame.key.get_pressed()
        player.update(keys)

        for g in goombas:
            g.update()
            if g.alive and player.rect.colliderect(g.rect):
                if player.vy > 0 and player.rect.bottom <= g.rect.centery:
                    g.alive = False
                    player.vy = -10
                else:
                    player.rect.x, player.rect.y = player_start_x, player_start_y
                    player.vy = 0

        # Camera follow
        target_x = player.rect.centerx - SCREEN_WIDTH // 2
        camera_x = max(0, min(target_x, len(level[0]) * TILE_SIZE - SCREEN_WIDTH))

        # Draw
        screen.fill(SKY_BLUE)
        for y, row in enumerate(level):
            for x, tile in enumerate(row):
                rect = pygame.Rect(x * TILE_SIZE - camera_x, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if tile == 1:
                    pygame.draw.rect(screen, GROUND_BROWN, rect)
                if tile == 2:
                    pygame.draw.rect(screen, BRICK_RED, rect)
                if tile == 3:
                    pygame.draw.rect(screen, QUESTION_YELLOW, rect)

        for g in goombas:
            g.draw(screen, camera_x)

        rect = player.rect.copy()
        rect.x -= camera_x
        pygame.draw.rect(screen, PLAYER_COLOR, rect)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
