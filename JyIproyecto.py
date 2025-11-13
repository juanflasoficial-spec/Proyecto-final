import pygame
import sys
from collections import deque

# -------------------------
# CONFIGURACIÓN BÁSICA
# -------------------------
TILE = 32
FPS = 60
TOP_OFFSET = 64  # espacio para HUD

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
VULNERABLE_BLUE = (50, 150, 255)

# VELOCIDADES
PACMAN_SPEED = 2.0
GHOST_SPEED  = 1.8
VULNERABLE_SPEED = 1.2

# DURACIÓN del estado vulnerable (en frames)
VULNERABLE_DURATION = FPS * 8  # 8 segundos

# -------------------------
# MAPA
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
    return 0 <= row < ROWS and 0 <= col < COLS and MAP_LAYOUT[row][col] == '#'

def is_tunnel(col, row):
    return 0 <= row < ROWS and 0 <= col < COLS and MAP_LAYOUT[row][col] == 'T'

# -------------------------
# PELLETS
# -------------------------
class Pellets:
    def __init__(self):
        self.small = set()
        self.power = set()
        for r, row in enumerate(MAP_LAYOUT):
            for c, ch in enumerate(row):
                if ch == '.': self.small.add((c,r))
                elif ch == 'o': self.power.add((c,r))
        self.total = len(self.small)+len(self.power)

    def draw(self, surf):
        for (c,r) in self.small:
            x,y = grid_to_px(c,r)
            pygame.draw.circle(surf, WHITE, (x+TILE//2, y+TILE//2), 3)
        for (c,r) in self.power:
            x,y = grid_to_px(c,r)
            pygame.draw.circle(surf, GREEN, (x+TILE//2, y+TILE//2), 7, 2)

    def eat_at(self, col,row):
        ate_small = ate_power = False
        if (col,row) in self.small:
            self.small.remove((col,row))
            ate_small = True
        elif (col,row) in self.power:
            self.power.remove((col,row))
            ate_power = True
        return ate_small, ate_power

    def empty(self):
        return len(self.small)==0 and len(self.power)==0

# -------------------------
# PACMAN
# -------------------------
class Pacman:
    def __init__(self,col,row):
        self.spawn_col = col
        self.spawn_row = row
        self.reset()

    def reset(self):
        self.col = self.spawn_col
        self.row = self.spawn_row
        self.x, self.y = grid_to_px(self.col, self.row)
        self.dir = pygame.Vector2(0,0)
        self.next_dir = pygame.Vector2(0,0)
        self.radius = TILE//2 - 2

    def set_next_dir(self, dx, dy):
        self.next_dir = pygame.Vector2(dx,dy)

    def can_move(self, dir_vec):
        nx = self.x + dir_vec.x * PACMAN_SPEED
        ny = self.y + dir_vec.y * PACMAN_SPEED
        target_cols = [int(nx // TILE), int((nx+TILE-1)//TILE)]
        target_rows = [int((ny-TOP_OFFSET)//TILE), int((ny-TOP_OFFSET+TILE-1)//TILE)]
        for tc in target_cols:
            for tr in target_rows:
                if is_wall(tc,tr): return False
        return True

    def update(self):
        if self.next_dir.length_squared()>0:
            cx = (self.x + TILE/2)%TILE
            cy = (self.y - TOP_OFFSET + TILE/2)%TILE
            if abs(cx - TILE/2)<2 and abs(cy - TILE/2)<2 and self.can_move(self.next_dir):
                self.dir = self.next_dir
                self.next_dir = pygame.Vector2(0,0)
        if self.can_move(self.dir):
            self.x += self.dir.x * PACMAN_SPEED
            self.y += self.dir.y * PACMAN_SPEED
        else:
            self.dir.update(0,0)
        col,row = px_to_grid(self.x,self.y)
        if is_tunnel(col,row):
            self.x = TILE if col>COLS//2 else (COLS-2)*TILE
        self.col,self.row = px_to_grid(self.x,self.y)

    def draw(self,surf):
        pygame.draw.circle(surf, YELLOW, (int(self.x+TILE//2), int(self.y+TILE//2)), self.radius)

# -------------------------
# GHOST
# -------------------------
class Ghost:
    COLORS = [RED, PINK, CYAN, ORANGE]
    def __init__(self,col,row,color=RED):
        self.spawn_col = col
        self.spawn_row = row
        self.color = color
        self.reset()

    def reset(self):
        self.col = self.spawn_col
        self.row = self.spawn_row
        self.x,self.y = grid_to_px(self.col,self.row)
        self.dir = pygame.Vector2(1,0)
        self.vulnerable = False
        self.vulnerable_timer = 0

    def neighbors(self,col,row):
        opts=[]
        for dc,dr in [(1,0),(-1,0),(0,1),(0,-1)]:
            if not is_wall(col+dc,row+dr):
                opts.append((dc,dr))
        return opts

    def choose_dir_basic(self,pac_col,pac_row):
        best=None; best_dist=1e9
        cur=(int(self.dir.x),int(self.dir.y))
        for dc,dr in self.neighbors(self.col,self.row):
            if (-dc,-dr)==cur and len(self.neighbors(self.col,self.row))>1: continue
            d = abs(pac_col-(self.col+dc)) + abs(pac_row-(self.row+dr))
            if d<best_dist: best_dist=d; best=(dc,dr)
        if best is None: best = self.neighbors(self.col,self.row)[0] if self.neighbors(self.col,self.row) else (0,0)
        return pygame.Vector2(best[0],best[1])

    def update(self,pac_col,pac_row):
        # Actualiza estado vulnerable
        if self.vulnerable:
            self.vulnerable_timer -= 1
            if self.vulnerable_timer <= 0:
                self.vulnerable = False

        cx = (self.x+TILE/2)%TILE
        cy = (self.y-TOP_OFFSET+TILE/2)%TILE
        if abs(cx-TILE/2)<2 and abs(cy-TILE/2)<2:
            self.col,self.row = px_to_grid(self.x,self.y)
            if self.vulnerable:
                # Cuando es vulnerable, huye de Pacman
                best = None
                best_dist = -1
                cur = (int(self.dir.x), int(self.dir.y))
                for dc,dr in self.neighbors(self.col,self.row):
                    if (-dc,-dr)==cur and len(self.neighbors(self.col,self.row))>1:
                        continue
                    d = abs(pac_col-(self.col+dc)) + abs(pac_row-(self.row+dr))
                    if d > best_dist:
                        best_dist = d
                        best = (dc,dr)
                if best is None:
                    best = self.neighbors(self.col,self.row)[0] if self.neighbors(self.col,self.row) else (0,0)
                self.dir = pygame.Vector2(best[0],best[1])
            else:
                # Normal: persigue a Pacman
                self.dir = self.choose_dir_basic(pac_col,pac_row)
        speed = VULNERABLE_SPEED if self.vulnerable else GHOST_SPEED
        self.x += self.dir.x * speed
        self.y += self.dir.y * speed
        col,row = px_to_grid(self.x,self.y)
        if is_tunnel(col,row):
            self.x = TILE if col>COLS//2 else (COLS-2)*TILE
        self.col,self.row = px_to_grid(self.x,self.y)

    def draw(self,surf):
        x=int(self.x+TILE//2); y=int(self.y+TILE//2)
        body=pygame.Rect(x-TILE//2+2,y-TILE//2+4,TILE-4,TILE-6)
        color = VULNERABLE_BLUE if self.vulnerable else self.color
        pygame.draw.ellipse(surf,color,body)
        base=pygame.Rect(x-TILE//2+2,y,TILE-4,TILE//2-2)
        pygame.draw.rect(surf,color,base)
        pygame.draw.circle(surf,WHITE,(x-6,y-4),4)
        pygame.draw.circle(surf,WHITE,(x+6,y-4),4)
        eye_color = NAVY if not self.vulnerable else WHITE
        pupil_color = WHITE if not self.vulnerable else NAVY
        pygame.draw.circle(surf,eye_color,(x-6,y-4),2)
        pygame.draw.circle(surf,eye_color,(x+6,y-4),2)
        pygame.draw.circle(surf,pupil_color,(x-6,y-4),1)
        pygame.draw.circle(surf,pupil_color,(x+6,y-4),1)

# -------------------------
# GAME
# -------------------------
class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        try:
            pygame.mixer.music.load(MUSIC_FILE)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)
        except: pass

        self.screen = pygame.display.set_mode((WIDTH,HEIGHT))
        pygame.display.set_caption("Pac-Man")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial",22,bold=True)

        self.walls = [pygame.Rect(*grid_to_px(c,r),TILE,TILE) for r,row in enumerate(MAP_LAYOUT) for c,ch in enumerate(row) if ch=='#']

        p_spawns = [(c,r) for r,row in enumerate(MAP_LAYOUT) for c,ch in enumerate(row) if ch=='P'] or [(1,1)]
        g_spawns = [(c,r) for r,row in enumerate(MAP_LAYOUT) for c,ch in enumerate(row) if ch=='G'] or [(COLS-2,1)]
        self.pacman = Pacman(*p_spawns[0])
        self.ghosts = [Ghost(*pos,color=Ghost.COLORS[i%4]) for i,pos in enumerate(g_spawns)]
        self.pellets = Pellets()
        self.score=0; self.lives=3; self.state="play"; self.paused=False

    def handle_events(self):
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            elif e.type==pygame.KEYDOWN:
                if e.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if self.state=="play":
                    if e.key in (pygame.K_LEFT,pygame.K_a): self.pacman.set_next_dir(-1,0)
                    elif e.key in (pygame.K_RIGHT,pygame.K_d): self.pacman.set_next_dir(1,0)
                    elif e.key in (pygame.K_UP,pygame.K_w): self.pacman.set_next_dir(0,-1)
                    elif e.key in (pygame.K_DOWN,pygame.K_s): self.pacman.set_next_dir(0,1)
                    elif e.key==pygame.K_p:
                        self.paused = not self.paused
                        pygame.mixer.music.pause() if self.paused else pygame.mixer.music.unpause()
                elif self.state=="gameover" and e.key==pygame.K_RETURN: self.restart()

    def update(self):
        if self.state!="play" or self.paused: return
        self.pacman.update()
        ate_small, ate_power = self.pellets.eat_at(self.pacman.col,self.pacman.row)
        if ate_small: self.score+=10
        if ate_power:
            self.score+=50
            for g in self.ghosts:
                g.vulnerable = True
                g.vulnerable_timer = VULNERABLE_DURATION
        for g in self.ghosts: g.update(self.pacman.col,self.pacman.row)
        self.check_collisions()
        if self.pellets.empty(): self.next_level()

    def check_collisions(self):
        p_rect=pygame.Rect(self.pacman.x+TILE//2-12,self.pacman.y+TILE//2-12,24,24)
        for g in self.ghosts:
            g_rect=pygame.Rect(g.x+TILE//2-12,g.y+TILE//2-12,24,24)
            if p_rect.colliderect(g_rect):
                if g.vulnerable:
                    # Come fantasma vulnerable
                    self.score += 200
                    g.reset()
                    g.vulnerable = False
                    g.vulnerable_timer = 0
                else:
                    self.lose_life()
                break

    def lose_life(self):
        self.lives-=1
        if self.lives<=0:
            self.state="gameover"; pygame.mixer.music.stop()
        else:
            self.pacman.reset()
            for g in self.ghosts: g.reset()

    def next_level(self):
        self.pellets=Pellets()
        self.pacman.reset()
        for g in self.ghosts: g.reset()

    def restart(self):
        self.__init__()
        try: pygame.mixer.music.play(-1)
        except: pass

    def draw_grid(self,surf):
        surf.fill(NAVY)
        for w in self.walls:
            pygame.draw.rect(surf,BLUE,w)
            pygame.draw.rect(surf,BLACK,w,2)

    def draw_hud(self,surf):
        pygame.draw.rect(surf,BLACK,(0,0,WIDTH,TOP_OFFSET))
        surf.blit(self.font.render(f"Score: {self.score}",True,WHITE),(16,16))
        surf.blit(self.font.render(f"Vidas: {self.lives}",True,WHITE),(220,16))
        if self.paused:
            overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            overlay.fill((0,0,0,160))
            surf.blit(overlay,(0,0))
            t=self.font.render("PAUSA (P)",True,WHITE)
            surf.blit(t,(WIDTH//2-t.get_width()//2,HEIGHT//2-20))

    def draw_gameover(self,surf):
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        surf.blit(overlay,(0,0))
        t1=self.font.render("GAME OVER",True,WHITE)
        t2=self.font.render("ENTER para reiniciar",True,WHITE)
        surf.blit(t1,(WIDTH//2-t1.get_width()//2,HEIGHT//2-30))
        surf.blit(t2,(WIDTH//2-t2.get_width()//2,HEIGHT//2+10))

    def draw(self):
        self.draw_grid(self.screen)
        self.pellets.draw(self.screen)
        for g in self.ghosts: g.draw(self.screen)
        self.pacman.draw(self.screen)
        self.draw_hud(self.screen)
        if self.state=="gameover": self.draw_gameover(self.screen)

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)

if __name__=="__main__":
    Game().run()
