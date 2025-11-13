"""
==========================================
PROYECTO FINAL - JUEGO PACMAN EN PYTHON
==========================================

Estudiantes:
------------
- Juan ..................................................
  🔸 Rol: Programador de lógica e inteligencia del juego.
  🔸 Tareas (breve descripción):
      1) POWER-PELLETS: activar "modo asustado" en los fantasmas por N segundos
         cuando Pac-Man coma un power-pellet (cambia color/velocidad; si Pac-Man
         toca un fantasma asustado, lo come, gana puntos y el fantasma vuelve a
         la casa con temporizador de respawn).
      2) MÁS FANTASMAS Y COMPORTAMIENTOS: mínimo 2 fantasmas nuevos con targets
         distintos; alternar estados chase/scatter con temporizador simple.
      3) RESPAWN Y CASA: definir la "casa" de fantasmas; al ser comidos, vuelven
         a la casa y reaparecen tras T segundos.
      4) SUBIR NIVEL: al limpiar todos los pellets pasar de nivel (puede aumentar
         ligeramente la velocidad o acortar temporizadores).

- Isaac ..................................................
  🔸 Rol: Diseñador de interfaz, sonido y experiencia visual (UX).
  🔸 Tareas (breve descripción):
      1) MENÚ INICIAL + PAUSA: pantalla de inicio (Jugar/Salir) y pausa con overlay
         semitransparente (tecla P).
      2) AUDIO Y FUENTES: sonidos para comer pellet/power/muerte/ghost; música de
         fondo; fuente TTF retro para HUD/menús.
      3) SPRITES/ANIMACIONES: reemplazar formas por sprites animados (Pac-Man y
         fantasmas); animación de muerte y parpadeo de fantasma asustado.
      4) RÉCORD (PERSISTENCIA): leer/guardar highscore en archivo `highscore.dat`.


import pygame
import sys
from collections import deque

# -------------------------
# CONFIGURACIÓN BÁSICA
# -------------------------
TILE = 32
FPS = 60
TOP_OFFSET = 64  # espacio para marcador HUD

# ARCHIVO DE MÚSICA DE FONDO
# Cambia el nombre del archivo para usar otra canción (debe estar en la misma carpeta)
MUSIC_FILE = "pacman.mp3"

# COLORES
BLACK   = (0, 0, 0)
NAVY    = (10, 10, 40)
BLUE    = (33, 66, 255)
YELLOW  = (255, 210, 0)
WHITE   = (240, 240, 240)
RED     = (255, 64, 64)
CYAN    = (64, 255, 255)
PINK    = (255, 128, 192)
ORANGE  = (255, 160, 64)
GREEN   = (50, 220, 120)
GREY    = (60, 60, 60)

# VELOCIDADES
PACMAN_SPEED = 2.0
GHOST_SPEED  = 1.8

# -------------------------
# MAPA (ASCII)
# -------------------------
MAP_LAYOUT = [
"########################",
"#..........##..........#",
"#.###.###..##..###.###.#",
"#o###.###..##..###.###o#",
"#......................#",
"#.###.#.######.#.###.#.#",
"#.....#....##..#.....#.#",
"#####.### #### #######.#",
"#    .# . GG   #..   TT#",
"#####.#.######.#.#######",
"#..........##..........#",
"#.###.###..##PP###.###.#",
"#o..#..............o...#",
"###.#.#.######.#.#.###.#",
"#.....#....##..#.....#.#",
"#.########.##.########T#",
"#......................#",
"########################",
]

ROWS = len(MAP_LAYOUT)
COLS = len(MAP_LAYOUT[0])
assert all(len(row) == COLS for row in MAP_LAYOUT), "Mapa irregular: filas con longitudes distintas"

WIDTH  = COLS * TILE
HEIGHT = TOP_OFFSET + ROWS * TILE

# -------------------------
# UTILIDADES
# -------------------------
def grid_to_px(col, row):
    return col * TILE, TOP_OFFSET + row * TILE

def px_to_grid(x, y):
    gy = max(0, (y - TOP_OFFSET) // TILE)
    gx = x // TILE
    return int(gx), int(gy)

def is_wall(col, row):
    if 0 <= row < ROWS and 0 <= col < COLS:
        return MAP_LAYOUT[row][col] == '#'
    return True

def is_tunnel(col, row):
    if 0 <= row < ROWS and 0 <= col < COLS:
        return MAP_LAYOUT[row][col] == 'T'
    return False

def is_path(col, row):
    if 0 <= row < ROWS and 0 <= col < COLS:
        return MAP_LAYOUT[row][col] in (' ', '.', 'o', 'P', 'G', 'T')
    return False

# -------------------------
# MANEJO DE PELLETS
# -------------------------
class Pellets:
    def __init__(self):
        self.small = set()
        self.power = set()
        for r, row in enumerate(MAP_LAYOUT):
            for c, ch in enumerate(row):
                if ch == '.':
                    self.small.add((c, r))
                elif ch == 'o':
                    self.power.add((c, r))
        self.total = len(self.small) + len(self.power)

    def draw(self, surf):
        for (c, r) in self.small:
            x, y = grid_to_px(c, r)
            pygame.draw.circle(surf, WHITE, (x + TILE//2, y + TILE//2), 3)
        for (c, r) in self.power:
            x, y = grid_to_px(c, r)
            pygame.draw.circle(surf, GREEN, (x + TILE//2, y + TILE//2), 7, 2)

    def eat_at(self, col, row):
        ate_small = False
        ate_power = False
        if (col, row) in self.small:
            self.small.remove((col, row))
            ate_small = True
        elif (col, row) in self.power:
            self.power.remove((col, row))
            ate_power = True
        return ate_small, ate_power

    def empty(self):
        return len(self.small) == 0 and len(self.power) == 0

# -------------------------
# ENTIDADES
# -------------------------
class Pacman:
    def __init__(self, col, row):
        self.spawn_col = col
        self.spawn_row = row
        self.reset()

    def reset(self):
        self.col = self.spawn_col
        self.row = self.spawn_row
        self.x, self.y = grid_to_px(self.col, self.row)
        self.dir = pygame.Vector2(0, 0)
        self.next_dir = pygame.Vector2(0, 0)
        self.radius = TILE//2 - 2

    def set_next_dir(self, dx, dy):
        self.next_dir = pygame.Vector2(dx, dy)

    def can_move(self, dir_vec):
        nx = self.x + dir_vec.x * PACMAN_SPEED
        ny = self.y + dir_vec.y * PACMAN_SPEED
        target_col_left   = int((nx) // TILE)
        target_col_right  = int((nx + TILE - 1) // TILE)
        target_row_top    = int((ny - TOP_OFFSET) // TILE)
        target_row_bottom = int((ny - TOP_OFFSET + TILE - 1) // TILE)
        for tc in (target_col_left, target_col_right):
            for tr in (target_row_top, target_row_bottom):
                if is_wall(tc, tr):
                    return False
        return True

    def update(self):
        if self.next_dir.length_squared() > 0:
            cx = (self.x + TILE/2) % TILE
            cy = (self.y - TOP_OFFSET + TILE/2) % TILE
            centered = (abs(cx - TILE/2) < 2 and abs(cy - TILE/2) < 2)
            if centered:
                if self.can_move(self.next_dir):
                    self.dir = self.next_dir
                    self.next_dir = pygame.Vector2(0, 0)
        if self.can_move(self.dir):
            self.x += self.dir.x * PACMAN_SPEED
            self.y += self.dir.y * PACMAN_SPEED
        else:
            self.dir.update(0, 0)

        col, row = px_to_grid(self.x, self.y)
        if is_tunnel(col, row):
            if col < COLS // 2:
                self.x, self.y = grid_to_px(COLS - 2, row)
            else:
                self.x, self.y = grid_to_px(1, row)

        self.col, self.row = px_to_grid(self.x, self.y)

    def draw(self, surf):
        pygame.draw.circle(surf, YELLOW, (int(self.x + TILE//2), int(self.y + TILE//2)), self.radius)
        if self.dir.length_squared() > 0:
            ang = 0
            if self.dir.x > 0:   ang = 0
            elif self.dir.x < 0: ang = 180
            elif self.dir.y < 0: ang = 90
            elif self.dir.y > 0: ang = 270
            mouth = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            pygame.draw.polygon(mouth, (0, 0, 0, 255), [(16,16),(32,8),(32,24)])
            mouth = pygame.transform.rotate(mouth, -ang)
            surf.blit(mouth, (self.x, self.y))

class Ghost:
    def __init__(self, col, row, color=RED):
        self.spawn_col = col
        self.spawn_row = row
        self.color = color
        self.reset()
        self.state = "chase"
        self.fright_timer = 0

    def reset(self):
        self.col = self.spawn_col
        self.row = self.spawn_row
        self.x, self.y = grid_to_px(self.col, self.row)
        self.dir = pygame.Vector2(1, 0)

    def neighbors(self, col, row):
        options = []
        for dc, dr in [(1,0),(-1,0),(0,1),(0,-1)]:
            nc, nr = col+dc, row+dr
            if not is_wall(nc, nr):
                options.append((dc, dr))
        return options

    def choose_dir_basic(self, pac_col, pac_row):
        best = None
        best_dist = 1e9
        cur = (int(self.dir.x), int(self.dir.y))
        for dc, dr in self.neighbors(self.col, self.row):
            if (-dc, -dr) == cur and len(self.neighbors(self.col, self.row)) > 1:
                continue
            d = abs(pac_col - (self.col + dc)) + abs(pac_row - (self.row + dr))
            if d < best_dist:
                best_dist = d
                best = (dc, dr)
        if best is None:
            opts = self.neighbors(self.col, self.row)
            best = opts[0] if opts else (0, 0)
        return pygame.Vector2(best[0], best[1])

    def update(self, pac_col, pac_row):
        cx = (self.x + TILE/2) % TILE
        cy = (self.y - TOP_OFFSET + TILE/2) % TILE
        centered = (abs(cx - TILE/2) < 2 and abs(cy - TILE/2) < 2)
        if centered:
            self.col, self.row = px_to_grid(self.x, self.y)
            self.dir = self.choose_dir_basic(pac_col, pac_row)
        self.x += self.dir.x * GHOST_SPEED
        self.y += self.dir.y * GHOST_SPEED
        col, row = px_to_grid(self.x, self.y)
        if is_tunnel(col, row):
            if col < COLS // 2:
                self.x, self.y = grid_to_px(COLS - 2, row)
            else:
                self.x, self.y = grid_to_px(1, row)
        self.col, self.row = px_to_grid(self.x, self.y)

    def draw(self, surf):
        x, y = int(self.x + TILE//2), int(self.y + TILE//2)
        body = pygame.Rect(x - TILE//2 + 2, y - TILE//2 + 4, TILE - 4, TILE - 6)
        pygame.draw.ellipse(surf, self.color, body)
        base = pygame.Rect(x - TILE//2 + 2, y, TILE - 4, TILE//2 - 2)
        pygame.draw.rect(surf, self.color, base)
        pygame.draw.circle(surf, WHITE, (x - 6, y - 4), 4)
        pygame.draw.circle(surf, WHITE, (x + 6, y - 4), 4)
        pygame.draw.circle(surf, NAVY,  (x - 6, y - 4), 2)
        pygame.draw.circle(surf, NAVY,  (x + 6, y - 4), 2)

# -------------------------
# JUEGO
# -------------------------
class Game:
    def __init__(self):
        pygame.init()

        # AUDIO: inicializar mezclador y reproducir música de fondo
        pygame.mixer.init()
        try:
            pygame.mixer.music.load(MUSIC_FILE)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)
            print(f"Música de fondo reproducida: {MUSIC_FILE}")
        except Exception as e:
            print(f"No se pudo cargar la música '{MUSIC_FILE}':", e)

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Pac-Man (versión educativa)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22, bold=True)

        self.walls = []
        for r, row in enumerate(MAP_LAYOUT):
            for c, ch in enumerate(row):
                if ch == '#':
                    self.walls.append(pygame.Rect(*grid_to_px(c, r), TILE, TILE))

        p_spawns, g_spawns = [], []
        for r, row in enumerate(MAP_LAYOUT):
            for c, ch in enumerate(row):
                if ch == 'P': p_spawns.append((c, r))
                elif ch == 'G': g_spawns.append((c, r))
        if not p_spawns: p_spawns = [(1, 1)]
        if not g_spawns: g_spawns = [(COLS - 2, 1)]

        self.pacman = Pacman(*p_spawns[0])
        self.ghosts = [Ghost(*g_spawns[0], color=RED)]
        self.pellets = Pellets()
        self.score = 0
        self.lives = 3
        self.state = "play"
        self.paused = False
        self.highscore = 0

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if self.state == "play":
                    if e.key in (pygame.K_LEFT, pygame.K_a): self.pacman.set_next_dir(-1, 0)
                    elif e.key in (pygame.K_RIGHT, pygame.K_d): self.pacman.set_next_dir(1, 0)
                    elif e.key in (pygame.K_UP, pygame.K_w): self.pacman.set_next_dir(0, -1)
                    elif e.key in (pygame.K_DOWN, pygame.K_s): self.pacman.set_next_dir(0, 1)
                    elif e.key == pygame.K_p:
                        self.paused = not self.paused
                        if self.paused:
                            pygame.mixer.music.pause()
                        else:
                            pygame.mixer.music.unpause()
                elif self.state == "gameover" and e.key == pygame.K_RETURN:
                    self.restart()

    def update(self):
        if self.state != "play" or self.paused:
            return
        self.pacman.update()
        ate_small, ate_power = self.pellets.eat_at(self.pacman.col, self.pacman.row)
        if ate_small: self.score += 10
        if ate_power: self.score += 50
        for g in self.ghosts:
            g.update(self.pacman.col, self.pacman.row)
        self.check_collisions()
        if self.pellets.empty():
            self.next_level()

    def check_collisions(self):
        px = self.pacman.x + TILE//2
        py = self.pacman.y + TILE//2
        p_rect = pygame.Rect(px - 12, py - 12, 24, 24)
        for g in self.ghosts:
            gx = g.x + TILE//2
            gy = g.y + TILE//2
            g_rect = pygame.Rect(gx - 12, gy - 12, 24, 24)
            if p_rect.colliderect(g_rect):
                self.lose_life()
                break

    def lose_life(self):
        self.lives -= 1
        if self.lives <= 0:
            self.state = "gameover"
            pygame.mixer.music.stop()
        else:
            self.pacman.reset()
            for g in self.ghosts:
                g.reset()

    def next_level(self):
        self.pellets = Pellets()
        self.pacman.reset()
        for g in self.ghosts:
            g.reset()

    def restart(self):
        self.__init__()
        try:
            pygame.mixer.music.play(-1)
        except:
            pass

    def draw_grid(self, surf):
        surf.fill(NAVY)
        for w in self.walls:
            pygame.draw.rect(surf, BLUE, w)
            pygame.draw.rect(surf, BLACK, w, 2)

    def draw_hud(self, surf):
        pygame.draw.rect(surf, BLACK, (0, 0, WIDTH, TOP_OFFSET))
        score_txt = self.font.render(f"Score: {self.score}", True, WHITE)
        lives_txt = self.font.render(f"Vidas: {self.lives}", True, WHITE)
        hs_txt = self.font.render(f"Récord: {self.highscore}", True, WHITE)
        surf.blit(score_txt, (16, 16))
        surf.blit(lives_txt, (220, 16))
        surf.blit(hs_txt, (400, 16))
        if self.paused:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            surf.blit(overlay, (0, 0))
            t = self.font.render("PAUSA (P)", True, WHITE)
            surf.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - 20))

    def draw_gameover(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surf.blit(overlay, (0, 0))
        t1 = self.font.render("GAME OVER", True, WHITE)
        t2 = self.font.render("ENTER para reiniciar", True, WHITE)
        surf.blit(t1, (WIDTH//2 - t1.get_width()//2, HEIGHT//2 - 30))
        surf.blit(t2, (WIDTH//2 - t2.get_width()//2, HEIGHT//2 + 10))

    def draw(self):
        self.draw_grid(self.screen)
        self.pellets.draw(self.screen)
        for g in self.ghosts:
            g.draw(self.screen)
        self.pacman.draw(self.screen)
        self.draw_hud(self.screen)
        if self.state == "gameover":
            self.draw_gameover(self.screen)

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    while True:
        game.handle_events()
        game.update()
        game.draw()
        pygame.display.flip()
        game.clock.tick(FPS)
