#!/usr/bin/env python3
"""
wa_wa_engine.py — FILES=off single-file game engine

WA WA ENGINE v1.1 — a tiny Mario Maker-style editor with three style packs:
  * MINECRAFT   (blocks, grass, dirt, stone)
  * EARTHBOUND  (SNES JRPG overworld tiles)
  * SMB3        (Super Mario Bros. 3 style blocks)

Everything drawn procedurally in pygame. No PNG/JPG/sprite sheets.
No internet. No subprocesses. One .py, one window, ~60 FPS.

Python 3.14+ / pygame-ce
[C] Fan meme tribute, 2026 — FILES=off demo
Minecraft (C) Mojang. EarthBound (C) Nintendo / HAL. SMB3 (C) Nintendo.

1.1 changes:
  * Undo / redo per pack (Ctrl+Z, Ctrl+Y / Ctrl+Shift+Z); a whole drag is one step,
    and [C] clear / [F] fill are undoable.
  * Coyote time, jump buffer and variable jump height (tap = short hop).
  * WA WA guy is a real sprite: hitbox-sized, faces his direction, walk cycle,
    open "WA" mouth in the air.
  * Tile textures are seeded per (pack, tile) and identical on every run.
  * "UNSAVED - FILES=OFF" badge, and quitting a non-empty level needs a second press.
  * Palette labels each tile with a [solid] tag.
  * [F] fill ground uses the pack's first solid tile (EarthBound grass is walk-through).
"""
import os, sys, math, random, array
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
try:
    import pygame
except ImportError:
    print("pip install pygame-ce", file=sys.stderr); sys.exit(1)

# ---------------------------------------------------------------- constants
VERSION = "1.1"
W, H = 1024, 640
FPS = 60
TILE = 32
GRID_W, GRID_H = 24, 14         # visible edit area

BLACK   = (18, 18, 24)
WHITE   = (240, 240, 240)
GRAY    = (110, 110, 120)
GRAY_DK = (60, 60, 70)
GRAY_LT = (180, 180, 190)
UI_BG   = (30, 30, 44)
UI_PANEL= (44, 44, 60)
UI_HI   = (90, 90, 120)
UI_TEXT = (230, 230, 240)
UI_ACC  = (250, 200, 60)
UI_WARN = (240, 110, 80)

# --- Minecraft pack ---
MC_GRASS_TOP = (95, 159, 53)
MC_GRASS_SIDE= (134, 96, 67)
MC_DIRT      = (134, 96, 67)
MC_DIRT_DK   = (110, 78, 52)
MC_STONE     = (128, 128, 128)
MC_STONE_DK  = (100, 100, 100)
MC_WOOD      = (156, 112, 66)
MC_WOOD_DK   = (120, 84, 48)
MC_LEAF      = (60, 130, 60)
MC_LEAF_DK   = (40, 100, 40)
MC_SAND      = (219, 207, 163)
MC_SAND_DK   = (190, 178, 130)
MC_WATER     = (60, 100, 200)
MC_WATER_DK  = (40, 70, 160)
MC_LAVA      = (220, 90, 30)
MC_LAVA_DK   = (160, 60, 20)
MC_PLANK     = (170, 130, 80)

# --- EarthBound pack ---
EB_GRASS     = (110, 180, 90)
EB_GRASS_DK  = (80, 150, 60)
EB_DIRT      = (190, 140, 90)
EB_DIRT_DK   = (150, 110, 70)
EB_PATH      = (220, 200, 160)
EB_PATH_DK   = (180, 160, 120)
EB_WATER     = (60, 140, 220)
EB_WATER_DK  = (40, 100, 180)
EB_TREE      = (50, 100, 50)
EB_TREE_DK   = (30, 70, 30)
EB_HOUSE     = (220, 190, 140)
EB_HOUSE_DK  = (170, 140, 90)
EB_ROOF      = (200, 80, 80)
EB_ROOF_DK   = (150, 50, 50)
EB_FLOWER    = (250, 220, 100)
EB_SIGN      = (180, 130, 80)

# --- SMB3 pack ---
SMB_GND_TOP  = (220, 130, 60)
SMB_GND      = (200, 100, 40)
SMB_GND_DK   = (150, 70, 20)
SMB_BRICK    = (200, 90, 30)
SMB_BRICK_DK = (140, 60, 20)
SMB_QBLOCK   = (250, 200, 60)
SMB_QBLOCK_DK= (200, 150, 40)
SMB_USED     = (170, 120, 60)
SMB_PIPE     = (60, 180, 80)
SMB_PIPE_DK  = (40, 130, 60)
SMB_CLOUD    = (250, 250, 250)
SMB_CLOUD_DK = (200, 200, 210)
SMB_BUSH     = (60, 160, 60)
SKY_BLUE     = (107, 178, 250)

# --- WA WA guy ---
WAWA_BODY    = (250, 200, 60)
WAWA_SHADE   = (215, 160, 40)
WAWA_LINE    = (110, 70, 20)
WAWA_MOUTH   = (150, 40, 40)
WAWA_FEET    = (120, 60, 40)

# ---------------------------------------------------------------- tile packs
# draw_fn(surface, x, y, size). Speckle noise comes from _TEX_RNG, which is
# re-seeded per (pack, tile) before each draw, so textures are identical on
# every run and on every machine (str seeds hash with SHA-512, not hash()).
_TEX_RNG = random.Random()

def _frame(s, x, y, sz, col, col_dk=None, border=True):
    s.fill(col, (x, y, sz, sz))
    if col_dk and border:
        pygame.draw.rect(s, col_dk, (x, y, sz, sz), 2)

def _speckle(s, x, y, sz, col, n):
    for _ in range(n):
        s.set_at((x + _TEX_RNG.randint(2, sz - 3), y + _TEX_RNG.randint(2, sz - 3)), col)

def draw_empty(s, x, y, sz):
    pass                        # sky shows through (cache pre-fills it)

def draw_mc_grass(s, x, y, sz):
    _frame(s, x, y, sz, MC_GRASS_SIDE)
    s.fill(MC_GRASS_TOP, (x, y, sz, sz // 3))
    for i in range(0, sz, 4):
        s.set_at((x + i, y + sz // 3), MC_GRASS_TOP)

def draw_mc_dirt(s, x, y, sz):
    _frame(s, x, y, sz, MC_DIRT);  _speckle(s, x, y, sz, MC_DIRT_DK, 6)

def draw_mc_stone(s, x, y, sz):
    _frame(s, x, y, sz, MC_STONE); _speckle(s, x, y, sz, MC_STONE_DK, 8)

def draw_mc_wood(s, x, y, sz):
    _frame(s, x, y, sz, MC_WOOD)
    s.fill(MC_WOOD_DK, (x, y, sz, 3))
    s.fill(MC_WOOD_DK, (x, y + sz - 3, sz, 3))
    s.fill(MC_WOOD_DK, (x + sz // 2 - 1, y, 2, sz))

def draw_mc_leaf(s, x, y, sz):
    _frame(s, x, y, sz, MC_LEAF);  _speckle(s, x, y, sz, MC_LEAF_DK, 10)

def draw_mc_sand(s, x, y, sz):
    _frame(s, x, y, sz, MC_SAND);  _speckle(s, x, y, sz, MC_SAND_DK, 6)

def draw_mc_water(s, x, y, sz):
    _frame(s, x, y, sz, MC_WATER)
    s.fill(MC_WATER_DK, (x, y + sz - 4, sz, 2))

def draw_mc_lava(s, x, y, sz):
    _frame(s, x, y, sz, MC_LAVA)
    s.fill(MC_LAVA_DK, (x, y + sz - 4, sz, 2))

def draw_mc_plank(s, x, y, sz):
    _frame(s, x, y, sz, MC_PLANK)
    s.fill(MC_WOOD_DK, (x, y + sz // 2 - 1, sz, 2))

def draw_eb_grass(s, x, y, sz):
    _frame(s, x, y, sz, EB_GRASS); _speckle(s, x, y, sz, EB_GRASS_DK, 6)

def draw_eb_dirt(s, x, y, sz):
    _frame(s, x, y, sz, EB_DIRT);  _speckle(s, x, y, sz, EB_DIRT_DK, 4)

def draw_eb_path(s, x, y, sz):
    _frame(s, x, y, sz, EB_PATH);  _speckle(s, x, y, sz, EB_PATH_DK, 4)

def draw_eb_water(s, x, y, sz):
    _frame(s, x, y, sz, EB_WATER)
    s.fill(EB_WATER_DK, (x, y + sz - 4, sz, 2))

def draw_eb_tree(s, x, y, sz):
    _frame(s, x, y, sz, EB_TREE)
    s.fill(EB_TREE_DK, (x + sz // 2 - 2, y + sz - 6, 4, 6))

def draw_eb_house(s, x, y, sz):
    _frame(s, x, y, sz, EB_HOUSE)
    s.fill(EB_HOUSE_DK, (x, y + sz - 4, sz, 4))

def draw_eb_roof(s, x, y, sz):
    _frame(s, x, y, sz, EB_ROOF)
    s.fill(EB_ROOF_DK, (x, y + sz - 4, sz, 4))

def draw_eb_flower(s, x, y, sz):
    _frame(s, x, y, sz, EB_GRASS)
    pygame.draw.circle(s, EB_FLOWER, (x + sz // 2, y + sz // 2), sz // 4)

def draw_eb_sign(s, x, y, sz):
    _frame(s, x, y, sz, EB_SIGN)
    s.fill(EB_DIRT_DK, (x + 2, y + 2, sz - 4, 2))

def draw_smb_ground(s, x, y, sz):
    _frame(s, x, y, sz, SMB_GND)
    s.fill(SMB_GND_TOP, (x, y, sz, 3))
    s.fill(SMB_GND_DK, (x, y + sz - 3, sz, 3))

def draw_smb_brick(s, x, y, sz):
    _frame(s, x, y, sz, SMB_BRICK)
    s.fill(SMB_BRICK_DK, (x, y + sz // 2 - 1, sz, 2))
    s.fill(SMB_BRICK_DK, (x + sz // 2 - 1, y, 2, sz))

def draw_smb_qblock(s, x, y, sz):
    _frame(s, x, y, sz, SMB_QBLOCK)
    s.fill(SMB_QBLOCK_DK, (x + 3, y + 3, sz - 6, 2))
    s.fill(SMB_QBLOCK_DK, (x + 3, y + sz - 5, sz - 6, 2))

def draw_smb_used(s, x, y, sz):
    _frame(s, x, y, sz, SMB_USED)

def draw_smb_pipe(s, x, y, sz):
    _frame(s, x, y, sz, SMB_PIPE)
    s.fill(SMB_PIPE_DK, (x, y, 4, sz))
    s.fill(SMB_PIPE_DK, (x + sz - 4, y, 4, sz))

def draw_smb_cloud(s, x, y, sz):
    s.fill(SKY_BLUE, (x, y, sz, sz))
    pygame.draw.circle(s, SMB_CLOUD, (x + sz // 2, y + sz // 2), sz // 3)
    pygame.draw.circle(s, SMB_CLOUD_DK, (x + sz // 2, y + sz // 2), sz // 3, 1)

def draw_smb_bush(s, x, y, sz):
    s.fill(SKY_BLUE, (x, y, sz, sz))
    pygame.draw.circle(s, SMB_BUSH, (x + sz // 2, y + sz // 2), sz // 3)

# Tiles: (name, draw_fn, solid) — list index is the tile id
MC_TILES = [
    ("Empty",   draw_empty,     False),
    ("Grass",   draw_mc_grass,  True),
    ("Dirt",    draw_mc_dirt,   True),
    ("Stone",   draw_mc_stone,  True),
    ("Wood",    draw_mc_wood,   True),
    ("Leaf",    draw_mc_leaf,   False),
    ("Sand",    draw_mc_sand,   True),
    ("Water",   draw_mc_water,  False),
    ("Lava",    draw_mc_lava,   False),
    ("Plank",   draw_mc_plank,  True),
]
EB_TILES = [
    ("Empty",   draw_empty,     False),
    ("Grass",   draw_eb_grass,  False),
    ("Dirt",    draw_eb_dirt,   False),
    ("Path",    draw_eb_path,   False),
    ("Water",   draw_eb_water,  False),
    ("Tree",    draw_eb_tree,   True),
    ("House",   draw_eb_house,  True),
    ("Roof",    draw_eb_roof,   False),
    ("Flower",  draw_eb_flower, False),
    ("Sign",    draw_eb_sign,   False),
]
SMB_TILES = [
    ("Empty",   draw_empty,     False),
    ("Ground",  draw_smb_ground,True),
    ("Brick",   draw_smb_brick, True),
    ("? Block", draw_smb_qblock,True),
    ("Used",    draw_smb_used,  True),
    ("Pipe",    draw_smb_pipe,  True),
    ("Cloud",   draw_smb_cloud, False),
    ("Bush",    draw_smb_bush,  False),
    ("Ground2", draw_smb_ground,True),
    ("Brick2",  draw_smb_brick, True),
]

PACKS = [
    ("MINECRAFT", MC_TILES, (110, 160, 220)),
    ("EARTHBOUND", EB_TILES, (60, 120, 200)),
    ("SMB3", SMB_TILES, SKY_BLUE),
]

# ---------------------------------------------------------------- world model
UNDO_LIMIT = 200                  # snapshots per pack (a 24x14 grid is tiny)

class World:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.grid = [[0] * w for _ in range(h)]  # tile id per cell
        self.undo_stack = []      # immutable grid snapshots, oldest first
        self.redo_stack = []
    def set(self, x, y, tid):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.grid[y][x] = tid
    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.grid[y][x]
        return 0
    def is_empty(self):
        return not any(any(row) for row in self.grid)
    def clear(self):
        self.grid = [[0] * self.w for _ in range(self.h)]

    # --- undo / redo
    def snapshot(self):
        return tuple(tuple(row) for row in self.grid)
    def restore(self, snap):
        self.grid = [list(row) for row in snap]
    def commit(self, before):
        """Record `before` as an undo step if the grid actually changed."""
        if before == self.snapshot():
            return False
        self.undo_stack.append(before)
        if len(self.undo_stack) > UNDO_LIMIT:
            del self.undo_stack[0]
        self.redo_stack.clear()
        return True
    def undo(self):
        if not self.undo_stack:
            return False
        self.redo_stack.append(self.snapshot())
        self.restore(self.undo_stack.pop())
        return True
    def redo(self):
        if not self.redo_stack:
            return False
        self.undo_stack.append(self.snapshot())
        self.restore(self.redo_stack.pop())
        return True

# ---------------------------------------------------------------- UI layout
VIEW_X, VIEW_Y = 200, 60
VIEW_W, VIEW_H = GRID_W * TILE, GRID_H * TILE     # 768 x 448
VIEW_RECT = pygame.Rect(VIEW_X, VIEW_Y, VIEW_W, VIEW_H)

PALETTE_X = 10
PALETTE_Y = 60
PALETTE_W = 180
PALETTE_H = GRID_H * TILE
PALETTE_RECT = pygame.Rect(PALETTE_X, PALETTE_Y, PALETTE_W, PALETTE_H)

TOOLBAR_H = 40
TOOLBAR_RECT = pygame.Rect(0, H - TOOLBAR_H, W, TOOLBAR_H)

QUIT_CONFIRM_MS = 2000            # second ESC / close within this window quits
TOAST_MS = 1600

# ---------------------------------------------------------------- play physics
SPAWN_X, SPAWN_Y = 2.0, 2.0       # player spawn, in tile units (top-left of hitbox)
PLAYER_W, PLAYER_H = 0.8, 1.0     # hitbox size, in tiles
MAX_DT = 1.0 / 30.0               # clamp frame time so a stall can't launch the player
MAX_STEP = 0.25                   # max travel per sub-step, in tiles (no tunnelling)
COLL_EPS = 1e-3

RUN_SPEED   = 6.0                 # tiles/s
RUN_ACCEL   = 40.0
GROUND_DRAG = 12.0
GRAVITY     = 30.0
MAX_FALL    = 20.0
JUMP_VY     = -12.0
COYOTE_TIME = 0.10                # s you can still jump after walking off a ledge
JUMP_BUFFER = 0.12                # s a jump pressed before landing is remembered
JUMP_CUT    = 0.45                # vy multiplier when jump is released while rising
JUMP_KEYS   = (pygame.K_SPACE, pygame.K_UP, pygame.K_w)

# ---------------------------------------------------------------- engine
class WaWaEngine:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init(22050, -16, 1, 256)
        except Exception:
            pass
        try:
            self.screen = pygame.display.set_mode((W, H), vsync=1)   # tear-free 60 FPS
        except (TypeError, pygame.error):
            self.screen = pygame.display.set_mode((W, H))            # no vsync support here
        pygame.display.set_caption(f"WA WA ENGINE v{VERSION} — FILES=off")
        self.clock = pygame.time.Clock()
        self.font_sm = pygame.font.Font(None, 20)
        self.font_md = pygame.font.Font(None, 24)
        self.font_lg = pygame.font.Font(None, 32)
        self.font_xl = pygame.font.Font(None, 64)
        self.worlds = [World(GRID_W, GRID_H) for _ in PACKS]   # one grid per pack
        self.pack_idx = 0
        self.selected_tile = 0
        self.mode = "edit"           # edit | play
        self.running = True
        self._stroke_before = None   # grid snapshot taken when a paint drag starts
        self._quit_armed_until = 0
        self._toast = ""
        self._toast_until = 0
        self.respawn()
        self._tile_cache = {}
        self._rebuild_tile_cache()
        # chomp beep for place
        self._place_beep = self._make_beep(440, 0.03, 4000)
        self._jump_beep  = self._make_beep(720, 0.05, 5000)

    def _make_beep(self, freq, dur, amp):
        try:
            if not pygame.mixer.get_init(): return None
            buf = array.array("h")
            for i in range(int(22050 * dur)):
                buf.append(int(amp * math.sin(2 * math.pi * freq * i / 22050)))
            return pygame.mixer.Sound(buffer=buf)
        except Exception:
            return None

    def _rebuild_tile_cache(self):
        self._tile_cache.clear()
        self._thumb_cache = {}
        for pname, tiles, sky in PACKS:
            for tid, (tname, dfn, solid) in enumerate(tiles):
                surf = pygame.Surface((TILE, TILE))
                surf.fill(sky)              # empty tiles show sky, not black
                _TEX_RNG.seed(f"wawa/{pname}/{tid}/{tname}")
                dfn(surf, 0, 0, TILE)
                self._tile_cache[(pname, tid)] = surf
                self._thumb_cache[(pname, tid)] = pygame.transform.scale(surf, (TILE - 8, TILE - 8))

    @property
    def world(self):
        return self.worlds[self.pack_idx]

    @property
    def current_pack(self):
        return PACKS[self.pack_idx]

    @property
    def current_sky(self):
        return self.current_pack[2]

    @property
    def current_tiles(self):
        return self.current_pack[1]

    @property
    def has_content(self):
        return any(not w.is_empty() for w in self.worlds)

    def ground_tile(self):
        """First solid tile of the current pack — what [F] lays down."""
        for tid, (_, _, solid) in enumerate(self.current_tiles):
            if solid:
                return tid
        return 1

    def tile_surface(self, pack_name, tid):
        return self._tile_cache.get((pack_name, tid))

    def is_solid(self, tx, ty):
        # Side walls are solid, sky above is open, and the pit below is open
        # so the player can fall out and respawn.
        if tx < 0 or tx >= self.world.w:
            return True
        if ty < 0 or ty >= self.world.h:
            return False
        tid = self.world.get(tx, ty)
        tiles = self.current_tiles
        return 0 < tid < len(tiles) and tiles[tid][2]

    def grid_to_screen(self, gx, gy):
        return VIEW_X + gx * TILE, VIEW_Y + gy * TILE

    def screen_to_grid(self, sx, sy):
        if not VIEW_RECT.collidepoint(sx, sy): return None
        return (sx - VIEW_X) // TILE, (sy - VIEW_Y) // TILE

    def toast(self, text, ms=TOAST_MS):
        self._toast = text
        self._toast_until = pygame.time.get_ticks() + ms

    # ------------------------------------------------ edit actions
    def _begin_stroke(self):
        if self._stroke_before is None:
            self._stroke_before = self.world.snapshot()

    def _end_stroke(self):
        if self._stroke_before is not None:
            self.world.commit(self._stroke_before)
            self._stroke_before = None

    def _paint(self, g, tid):
        self._begin_stroke()
        self.world.set(g[0], g[1], tid)

    def _edit_op(self, fn):
        """Run a whole-grid edit as one undo step."""
        self._end_stroke()
        before = self.world.snapshot()
        fn()
        self.world.commit(before)

    def undo(self):
        self._end_stroke()
        self.toast("Undo" if self.world.undo() else "Nothing to undo")

    def redo(self):
        self._end_stroke()
        self.toast("Redo" if self.world.redo() else "Nothing to redo")

    def request_quit(self):
        now = pygame.time.get_ticks()
        if not self.has_content or now < self._quit_armed_until:
            self.running = False
            return
        self._quit_armed_until = now + QUIT_CONFIRM_MS
        self.toast("FILES=OFF: level is not saved. Press again to quit.", QUIT_CONFIRM_MS)

    # ------------------------------------------------ input
    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.request_quit()
        elif e.type == pygame.KEYDOWN:
            ctrl = e.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)
            shift = e.mod & pygame.KMOD_SHIFT
            if e.key == pygame.K_ESCAPE:
                if self.mode == "play":
                    self.mode = "edit"
                else:
                    self.request_quit()
            elif e.key == pygame.K_TAB:
                self._end_stroke()
                self.pack_idx = (self.pack_idx + 1) % len(PACKS)
                self.selected_tile = 0
                if self.mode == "play":
                    self.respawn()             # new pack = new level layout
            elif e.key == pygame.K_RETURN:
                self._end_stroke()
                if self.mode == "edit":
                    self.mode = "play"
                    self.respawn()
                else:
                    self.mode = "edit"
            elif self.mode == "edit" and ctrl and e.key == pygame.K_z:
                self.redo() if shift else self.undo()
            elif self.mode == "edit" and ctrl and e.key == pygame.K_y:
                self.redo()
            elif self.mode == "edit" and not ctrl and e.key == pygame.K_c:
                self._edit_op(self.world.clear)
            elif self.mode == "edit" and not ctrl and e.key == pygame.K_f:
                w, gt = self.world, self.ground_tile()
                self._edit_op(lambda: [w.set(gx, w.h - 1, gt) for gx in range(w.w)])
            elif self.mode == "play" and e.key in JUMP_KEYS:
                self.jump_buffer = JUMP_BUFFER  # remembered until we can jump
        elif e.type == pygame.WINDOWFOCUSLOST:
            self._end_stroke()
        elif e.type == pygame.MOUSEBUTTONDOWN:
            mx, my = e.pos
            if self.mode == "edit" and e.button in (1, 3):   # wheel = 4/5, not a click
                if PALETTE_RECT.collidepoint(mx, my):
                    idx = (my - PALETTE_Y) // TILE
                    if 0 <= idx < len(self.current_tiles):
                        self.selected_tile = idx
                else:
                    g = self.screen_to_grid(mx, my)
                    if g:
                        if e.button == 1:
                            self._paint(g, self.selected_tile)
                            if self._place_beep: self._place_beep.play()
                        elif e.button == 3:
                            self._paint(g, 0)
            elif self.mode == "play" and e.button in (1, 2, 3):   # ignore scroll wheel
                self.mode = "edit"
        elif e.type == pygame.MOUSEBUTTONUP:
            if e.button in (1, 3):
                self._end_stroke()             # one drag = one undo step
        elif e.type == pygame.MOUSEMOTION and self.mode == "edit":
            if not (e.buttons[0] or e.buttons[2]):
                self._end_stroke()             # button-up was lost outside the window
                return
            g = self.screen_to_grid(*e.pos)
            if g and e.buttons[0]:
                self._paint(g, self.selected_tile)
            elif g and e.buttons[2]:
                self._paint(g, 0)

    # ------------------------------------------------ play physics
    def respawn(self):
        self.player_x, self.player_y = SPAWN_X, SPAWN_Y
        self.player_vx = self.player_vy = 0.0
        self.player_on_ground = False
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self._can_cut_jump = False
        self.facing = 1
        self.walk_phase = 0.0

    def update_play(self, dt):
        dt = min(dt, MAX_DT)                  # a window drag must not launch the player
        keys = pygame.key.get_pressed()
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        if left and not right:
            self.player_vx -= RUN_ACCEL * dt
            self.facing = -1
        elif right and not left:
            self.player_vx += RUN_ACCEL * dt
            self.facing = 1
        else:
            self.player_vx *= max(0.0, 1.0 - GROUND_DRAG * dt)
        self.player_vx = max(-RUN_SPEED, min(RUN_SPEED, self.player_vx))

        # Forgiving jumps: grounded within the last COYOTE_TIME, and the jump
        # was pressed within the last JUMP_BUFFER — order doesn't matter.
        if self.player_on_ground:
            self.coyote = COYOTE_TIME
        if self.jump_buffer > 0 and self.coyote > 0:
            self.player_vy = JUMP_VY
            self.player_on_ground = False
            self.coyote = self.jump_buffer = 0.0
            self._can_cut_jump = True
            if self._jump_beep: self._jump_beep.play()
        self.coyote = max(0.0, self.coyote - dt)
        self.jump_buffer = max(0.0, self.jump_buffer - dt)

        # Variable height: letting go while still rising cuts the jump short.
        if self._can_cut_jump:
            if self.player_vy >= 0:
                self._can_cut_jump = False
            elif not any(keys[k] for k in JUMP_KEYS):
                self.player_vy *= JUMP_CUT
                self._can_cut_jump = False

        self.player_vy = min(MAX_FALL, self.player_vy + GRAVITY * dt)

        # Split the frame into sub-steps so the player never crosses a whole
        # tile in one move, which is what let it pass through thin floors.
        travel = max(abs(self.player_vx), abs(self.player_vy)) * dt
        steps = max(1, math.ceil(travel / MAX_STEP))
        sdt = dt / steps
        for _ in range(steps):
            self._move_x(self.player_vx * sdt)
            self._move_y(self.player_vy * sdt)

        if self.player_on_ground:
            self.walk_phase += abs(self.player_vx) * dt * 2.2
        else:
            self.walk_phase = 0.0

        # Fell out of the level: respawn instead of falling forever.
        if self.player_y > self.world.h:
            self.respawn()

    def _overlaps(self, x, y):
        x0, y0 = math.floor(x), math.floor(y)
        x1 = math.floor(x + PLAYER_W - COLL_EPS)
        y1 = math.floor(y + PLAYER_H - COLL_EPS)
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if self.is_solid(tx, ty):
                    return True
        return False

    def _move_x(self, dx):
        if dx == 0:
            return
        nx = self.player_x + dx
        if not self._overlaps(nx, self.player_y):
            self.player_x = nx
            return
        # Blocked: snap flush against the wall face and stop horizontal motion.
        if dx > 0:
            wall = math.floor(nx + PLAYER_W - COLL_EPS)
            self.player_x = wall - PLAYER_W
        else:
            wall = math.floor(nx)
            self.player_x = wall + 1
        self.player_vx = 0.0

    def _move_y(self, dy):
        if dy == 0:
            return
        ny = self.player_y + dy
        if not self._overlaps(self.player_x, ny):
            self.player_y = ny
            self.player_on_ground = False
            return
        # Blocked: snap so the feet sit exactly on the floor, or the head
        # sits exactly under the ceiling.
        if dy > 0:
            floor_row = math.floor(ny + PLAYER_H - COLL_EPS)
            self.player_y = floor_row - PLAYER_H
            self.player_on_ground = True
        else:
            ceil_row = math.floor(ny)
            self.player_y = ceil_row + 1
            self.player_on_ground = False
        self.player_vy = 0.0

    # ------------------------------------------------ draw
    def draw_player(self, s):
        """WA WA guy, drawn to exactly fill the hitbox."""
        sx, sy = self.grid_to_screen(self.player_x, self.player_y)
        pw, ph = round(PLAYER_W * TILE), round(PLAYER_H * TILE)   # 26 x 32
        x, y = round(sx), round(sy)
        f = self.facing
        air = not self.player_on_ground

        # feet: alternate while walking, tuck together in the air
        swing = 0 if air else round(3 * math.sin(self.walk_phase * math.pi))
        foot_y = y + ph - 5
        for fx, lift in ((x + 3, swing), (x + pw - 11, -swing)):
            pygame.draw.rect(s, WAWA_FEET,
                             (fx, foot_y - max(0, lift), 8, 5), border_radius=2)

        # body: rounded blob, slight stretch when rising, squash when falling
        stretch = 0
        if air:
            stretch = 2 if self.player_vy < 0 else -1
        body = pygame.Rect(x + 1, y + 2 - stretch, pw - 2, ph - 7 + stretch)   # top >= y, bottom = y+ph-5
        pygame.draw.rect(s, WAWA_BODY, body, border_radius=8)
        pygame.draw.rect(s, WAWA_SHADE,
                         (body.x + 2, body.bottom - 6, body.w - 4, 4), border_radius=2)
        pygame.draw.rect(s, WAWA_LINE, body, 2, border_radius=8)

        # eyes look where he's going
        cx = body.centerx + 2 * f
        ey = body.y + 8
        for ex in (cx - 5, cx + 5):
            pygame.draw.ellipse(s, WHITE, (ex - 3, ey - 4, 6, 8))
            pygame.draw.rect(s, BLACK, (ex - 1 + f, ey - 2 + (1 if air and self.player_vy > 0 else 0), 2, 4))

        # mouth: big "WA" in the air, little grin on the ground
        my = body.y + 18
        if air:
            pygame.draw.ellipse(s, WAWA_MOUTH, (cx - 4, my - 2, 8, 7))
            pygame.draw.ellipse(s, WAWA_LINE, (cx - 4, my - 2, 8, 7), 1)
        else:
            pygame.draw.arc(s, WAWA_LINE, (cx - 5, my - 4, 10, 6), math.pi, 2 * math.pi, 2)

    def draw_toast(self, s):
        if pygame.time.get_ticks() >= self._toast_until or not self._toast:
            return
        img = self.font_md.render(self._toast, True, WHITE)
        box = img.get_rect(center=(VIEW_X + VIEW_W // 2, VIEW_Y + VIEW_H - 24)).inflate(20, 10)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((0, 0, 0, 190))
        s.blit(panel, box)
        s.blit(img, img.get_rect(center=box.center))

    def draw_edit(self):
        s = self.screen
        s.fill(UI_BG)
        # top bar
        pygame.draw.rect(s, UI_PANEL, (0, 0, W, 50))
        title = self.font_lg.render(f"WA WA ENGINE v{VERSION}", True, UI_ACC)
        s.blit(title, (14, 10))
        pack_name = self.current_pack[0]
        pack_img = self.font_md.render(f"PACK: {pack_name}   [TAB] cycle", True, UI_TEXT)
        s.blit(pack_img, (230, 16))
        w = self.world
        hist = self.font_sm.render(f"undo {len(w.undo_stack)}  redo {len(w.redo_stack)}",
                                   True, GRAY_LT)
        s.blit(hist, (560, 19))
        if self.has_content:
            badge = self.font_sm.render("UNSAVED - FILES=OFF", True, BLACK)
            r = badge.get_rect(topright=(W - 18, 17)).inflate(12, 8)
            pygame.draw.rect(s, UI_WARN, r, border_radius=4)
            s.blit(badge, badge.get_rect(center=r.center))
        # palette
        pygame.draw.rect(s, UI_PANEL, PALETTE_RECT)
        pygame.draw.rect(s, UI_HI, PALETTE_RECT, 2)
        for i, (tname, dfn, solid) in enumerate(self.current_tiles):
            py = PALETTE_Y + i * TILE
            if py + TILE > PALETTE_Y + PALETTE_H: break
            if i == self.selected_tile:
                pygame.draw.rect(s, UI_ACC, (PALETTE_X + 2, py + 2, PALETTE_W - 4, TILE - 4), 2)
            thumb = self._thumb_cache.get((pack_name, i))
            if thumb:
                s.blit(thumb, (PALETTE_X + 6, py + 4))
            label = self.font_sm.render(tname + ("  [solid]" if solid else ""), True,
                                        UI_TEXT if i == self.selected_tile else GRAY_LT)
            s.blit(label, (PALETTE_X + TILE + 6, py + (TILE - label.get_height()) // 2))
        # canvas
        pygame.draw.rect(s, self.current_sky, VIEW_RECT)
        for gy in range(GRID_H):
            for gx in range(GRID_W):
                tid = w.get(gx, gy)
                if tid:
                    surf = self.tile_surface(pack_name, tid)
                    if surf:
                        s.blit(surf, (VIEW_X + gx * TILE, VIEW_Y + gy * TILE))
        pygame.draw.rect(s, UI_HI, VIEW_RECT, 2)
        # grid lines
        for gx in range(GRID_W + 1):
            pygame.draw.line(s, (50, 50, 70), (VIEW_X + gx * TILE, VIEW_Y),
                             (VIEW_X + gx * TILE, VIEW_Y + VIEW_H), 1)
        for gy in range(GRID_H + 1):
            pygame.draw.line(s, (50, 50, 70), (VIEW_X, VIEW_Y + gy * TILE),
                             (VIEW_X + VIEW_W, VIEW_Y + gy * TILE), 1)
        # spawn marker
        sx, sy = self.grid_to_screen(SPAWN_X, SPAWN_Y)
        pygame.draw.rect(s, UI_ACC, (sx, sy, PLAYER_W * TILE, PLAYER_H * TILE), 1)

        # bottom toolbar
        pygame.draw.rect(s, UI_PANEL, TOOLBAR_RECT)
        pygame.draw.rect(s, UI_HI, TOOLBAR_RECT, 2)
        tip = self.font_sm.render("LMB paint  RMB erase  Ctrl+Z undo  Ctrl+Y redo  [C] clear  "
                                  "[F] fill ground  [TAB] pack  [ENTER] play  [ESC] quit",
                                  True, UI_TEXT)
        s.blit(tip, (W // 2 - tip.get_width() // 2, H - TOOLBAR_H + 12))
        self.draw_toast(s)

    def draw_play(self):
        s = self.screen
        s.fill(self.current_sky)
        pack_name = self.current_pack[0]
        for gy in range(GRID_H):
            for gx in range(GRID_W):
                tid = self.world.get(gx, gy)
                if tid:
                    surf = self.tile_surface(pack_name, tid)
                    if surf:
                        s.blit(surf, (VIEW_X + gx * TILE, VIEW_Y + gy * TILE))
        self.draw_player(s)
        # overlay
        bar = pygame.Surface((W, 40)); bar.set_alpha(180); bar.fill(BLACK)
        s.blit(bar, (0, 0))
        info = self.font_md.render("[PLAY]  ARROWS/WASD move  SPACE jump (hold = higher)  "
                                   "ESC/ENTER to edit", True, WHITE)
        s.blit(info, (14, 10))
        self.draw_toast(s)

    def draw(self):
        if self.mode == "edit":
            self.draw_edit()
        else:
            self.draw_play()
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for e in pygame.event.get():
                self.handle_event(e)
            if self.mode == "play":
                self.update_play(dt)
            self.draw()
        pygame.quit()
        return 0


if __name__ == "__main__":
    raise SystemExit(WaWaEngine().run())
