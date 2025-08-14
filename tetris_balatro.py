import pygame
import random
import sys
from enum import Enum
from collections import Counter
import math

# Initialize Pygame
pygame.init()

# Constants - Using fullscreen
info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h

# Grid settings
GRID_WIDTH = 10
GRID_HEIGHT = 20
CELL_SIZE = min(SCREEN_WIDTH // 15, SCREEN_HEIGHT // 25)
GRID_X_OFFSET = SCREEN_WIDTH // 4
GRID_Y_OFFSET = SCREEN_HEIGHT // 2 - (GRID_HEIGHT * CELL_SIZE) // 2

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (50, 50, 50)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
GOLD = (255, 215, 0)
SILVER = (192, 192, 192)

# Tetromino shapes
SHAPES = [
    [[1, 1, 1, 1]],  # I (Straight)
    [[1, 1], [1, 1]],  # O
    [[0, 1, 0], [1, 1, 1]],  # T
    [[0, 1, 1], [1, 1, 0]],  # S
    [[1, 1, 0], [0, 1, 1]],  # Z
    [[1, 0, 0], [1, 1, 1]],  # J
    [[0, 0, 1], [1, 1, 1]]   # L
]

SHAPE_COLORS = [CYAN, YELLOW, PURPLE, GREEN, RED, BLUE, ORANGE]
SHAPE_NAMES = ["I (Straight)", "O (Square)", "T", "S", "Z", "J", "L"]

class GameState(Enum):
    MENU = 0
    PLAYING = 1
    SHOP = 2
    PACK_OPENING = 3
    GAME_OVER = 4

class PackType(Enum):
    BASIC = 0
    PREMIUM = 1
    STRAIGHT = 2

class Tetromino:
    def __init__(self, shape_index, x, y):
        self.shape_index = shape_index
        self.shape = SHAPES[shape_index]
        self.color = SHAPE_COLORS[shape_index]
        self.x = x
        self.y = y
        self.rotation = 0
        
    def rotate(self):
        # Rotate shape 90 degrees clockwise
        self.shape = [list(row) for row in zip(*self.shape[::-1])]
        
    def get_cells(self):
        cells = []
        for row_idx, row in enumerate(self.shape):
            for col_idx, cell in enumerate(row):
                if cell:
                    cells.append((self.x + col_idx, self.y + row_idx))
        return cells

class TetrisGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        pygame.display.set_caption("Tetris: Balatro Edition")
        self.clock = pygame.time.Clock()
        
        # Load fonts
        self.title_font = pygame.font.SysFont('Arial', 72, bold=True)
        self.large_font = pygame.font.SysFont('Arial', 48, bold=True)
        self.medium_font = pygame.font.SysFont('Arial', 36)
        self.font = pygame.font.SysFont('Arial', 24)
        self.small_font = pygame.font.SysFont('Arial', 20)
        
        self.reset_game()
        
    def reset_game(self):
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.current_piece = None
        self.next_piece_index = None
        self.score = 0
        self.lines_cleared = 0
        self.level = 1
        self.fall_time = 0
        self.fall_speed = 500  # milliseconds
        self.game_over = False
        self.state = GameState.MENU
        self.round_number = 1
        self.round_target = 1000
        self.money = 500  # Starting money
        
        # Initialize deck with one of each piece
        self.piece_deck = list(range(len(SHAPES)))
        self.next_piece_index = self.get_random_piece_from_deck()
        
        # Balatro-inspired mechanics
        self.jokers = []  # Active jokers
        self.upgrades = {
            'score_multiplier': 1.0,
            'extra_lines': 0,
            'hold_piece': False,
            'ghost_piece': False,
            'bomb_piece': False
        }
        
        self.held_piece = None
        self.can_hold = True
        
        # Pack opening variables
        self.pack_contents = []
        self.pack_opening_animation_time = 0
        self.pack_type = None
        
        # Menu animation
        self.menu_animation_time = 0
        
    def get_random_piece_from_deck(self):
        if not self.piece_deck:
            # If deck is empty, reset to default
            self.piece_deck = list(range(len(SHAPES)))
        return random.choice(self.piece_deck)
        
    def spawn_piece(self):
        shape_index = self.next_piece_index
        self.next_piece_index = self.get_random_piece_from_deck()
        
        # Bomb piece chance (Balatro-inspired)
        if self.upgrades['bomb_piece'] and random.random() < 0.1:
            # Create a special "bomb" piece that clears a 3x3 area
            self.current_piece = Tetromino(shape_index, GRID_WIDTH // 2 - 1, 0)
            self.current_piece.is_bomb = True
        else:
            self.current_piece = Tetromino(shape_index, GRID_WIDTH // 2 - 1, 0)
            self.current_piece.is_bomb = False
            
        self.can_hold = True
        
        # Check if game over
        if self.check_collision():
            self.game_over = True
            self.state = GameState.GAME_OVER
            
    def check_collision(self, dx=0, dy=0, piece=None):
        if piece is None:
            piece = self.current_piece
            if piece is None:
                return False
                
        for x, y in piece.get_cells():
            new_x, new_y = x + dx, y + dy
            if new_x < 0 or new_x >= GRID_WIDTH or new_y >= GRID_HEIGHT:
                return True
            if new_y >= 0 and self.grid[new_y][new_x]:
                return True
        return False
        
    def lock_piece(self):
        for x, y in self.current_piece.get_cells():
            if y >= 0:
                self.grid[y][x] = self.current_piece.shape_index + 1
                
        # Check for bomb piece effect
        if self.current_piece.is_bomb:
            self.explode_bomb(self.current_piece.x, self.current_piece.y)
            
        self.clear_lines()
        self.spawn_piece()
        
    def explode_bomb(self, bomb_x, bomb_y):
        # Clear a 3x3 area around the bomb
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                x, y = bomb_x + dx, bomb_y + dy
                if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
                    self.grid[y][x] = 0
                    
        # Add bonus points for bomb explosion
        self.score += 200 * self.upgrades['score_multiplier']
        
    def clear_lines(self):
        lines_to_clear = []
        
        for y in range(GRID_HEIGHT):
            if all(self.grid[y]):
                lines_to_clear.append(y)
                
        if lines_to_clear:
            # Remove cleared lines
            for y in lines_to_clear:
                del self.grid[y]
                self.grid.insert(0, [0 for _ in range(GRID_WIDTH)])
                
            # Calculate score with Balatro-inspired multipliers
            lines_cleared = len(lines_to_clear)
            base_score = [0, 100, 300, 500, 800][lines_cleared] * self.level
            
            # Apply joker effects
            for joker in self.jokers:
                if joker == 'Double Points':
                    base_score *= 2
                elif joker == 'Line Bonus':
                    base_score += 50 * lines_cleared
                    
            # Apply upgrades
            base_score *= self.upgrades['score_multiplier']
            base_score += self.upgrades['extra_lines'] * 100
            
            self.score += int(base_score)
            self.lines_cleared += lines_cleared
            
            # Level up every 10 lines
            if self.lines_cleared >= self.level * 10:
                self.level += 1
                self.fall_speed = max(100, self.fall_speed - 50)
                
    def move(self, dx, dy):
        if self.current_piece and not self.check_collision(dx, dy):
            self.current_piece.x += dx
            self.current_piece.y += dy
            return True
        return False
        
    def rotate_piece(self):
        if self.current_piece is None:
            return
            
        original_shape = self.current_piece.shape
        self.current_piece.rotate()
        
        # Check if rotation is valid
        if self.check_collision():
            # Try wall kicks
            for kick_x in [1, -1, 2, -2]:
                if not self.check_collision(kick_x, 0):
                    self.current_piece.x += kick_x
                    return
                    
            # Revert rotation if no valid position
            self.current_piece.shape = original_shape
            
    def hold_piece(self):
        if self.current_piece is None:
            return
            
        if self.upgrades['hold_piece'] and self.can_hold:
            if self.held_piece is None:
                self.held_piece = self.current_piece.shape_index
                self.spawn_piece()
            else:
                # Swap current and held piece
                self.held_piece, self.current_piece.shape_index = self.current_piece.shape_index, self.held_piece
                self.current_piece.shape = SHAPES[self.current_piece.shape_index]
                self.current_piece.color = SHAPE_COLORS[self.current_piece.shape_index]
                self.current_piece.x = GRID_WIDTH // 2 - 1
                self.current_piece.y = 0
            self.can_hold = False
            
    def hard_drop(self):
        if self.current_piece is None:
            return
            
        drop_distance = 0
        while self.move(0, 1):
            drop_distance += 1
        self.score += drop_distance * 2
        self.lock_piece()
        
    def update(self, dt):
        if self.state == GameState.PLAYING:
            if self.current_piece is not None:
                self.fall_time += dt
                if self.fall_time >= self.fall_speed:
                    self.move(0, 1)
                    self.fall_time = 0
                
            # Check if round is complete
            if self.score >= self.round_target:
                self.money += 100 + (self.round_number * 50)
                self.state = GameState.SHOP
                
        elif self.state == GameState.PACK_OPENING:
            self.pack_opening_animation_time += dt
            
        elif self.state == GameState.MENU:
            self.menu_animation_time += dt
            
    def draw_grid(self):
        # Clear the screen first
        self.screen.fill(BLACK)
        
        # Draw grid background with a subtle gradient
        for y in range(GRID_HEIGHT):
            color_value = 40 + (y * 2)
            color = (color_value, color_value, color_value + 5)
            pygame.draw.rect(self.screen, color, 
                            (GRID_X_OFFSET, GRID_Y_OFFSET + y * CELL_SIZE, 
                             GRID_WIDTH * CELL_SIZE, CELL_SIZE))
        
        # Draw grid lines
        for x in range(GRID_WIDTH + 1):
            pygame.draw.line(self.screen, DARK_GRAY, 
                            (GRID_X_OFFSET + x * CELL_SIZE, GRID_Y_OFFSET),
                            (GRID_X_OFFSET + x * CELL_SIZE, GRID_Y_OFFSET + GRID_HEIGHT * CELL_SIZE), 2)
        for y in range(GRID_HEIGHT + 1):
            pygame.draw.line(self.screen, DARK_GRAY, 
                            (GRID_X_OFFSET, GRID_Y_OFFSET + y * CELL_SIZE),
                            (GRID_X_OFFSET + GRID_WIDTH * CELL_SIZE, GRID_Y_OFFSET + y * CELL_SIZE), 2)
        
        # Draw placed pieces with a subtle 3D effect
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.grid[y][x]:
                    color = SHAPE_COLORS[self.grid[y][x] - 1]
                    # Main block
                    pygame.draw.rect(self.screen, color,
                                    (GRID_X_OFFSET + x * CELL_SIZE, GRID_Y_OFFSET + y * CELL_SIZE,
                                     CELL_SIZE - 2, CELL_SIZE - 2))
                    # Highlight
                    highlight_color = tuple(min(255, c + 50) for c in color)
                    pygame.draw.line(self.screen, highlight_color,
                                   (GRID_X_OFFSET + x * CELL_SIZE, GRID_Y_OFFSET + y * CELL_SIZE),
                                   (GRID_X_OFFSET + x * CELL_SIZE + CELL_SIZE - 2, GRID_Y_OFFSET + y * CELL_SIZE), 2)
                    pygame.draw.line(self.screen, highlight_color,
                                   (GRID_X_OFFSET + x * CELL_SIZE, GRID_Y_OFFSET + y * CELL_SIZE),
                                   (GRID_X_OFFSET + x * CELL_SIZE, GRID_Y_OFFSET + y * CELL_SIZE + CELL_SIZE - 2), 2)
                    # Shadow
                    shadow_color = tuple(max(0, c - 50) for c in color)
                    pygame.draw.line(self.screen, shadow_color,
                                   (GRID_X_OFFSET + x * CELL_SIZE + CELL_SIZE - 2, GRID_Y_OFFSET + y * CELL_SIZE),
                                   (GRID_X_OFFSET + x * CELL_SIZE + CELL_SIZE - 2, GRID_Y_OFFSET + y * CELL_SIZE + CELL_SIZE - 2), 2)
                    pygame.draw.line(self.screen, shadow_color,
                                   (GRID_X_OFFSET + x * CELL_SIZE, GRID_Y_OFFSET + y * CELL_SIZE + CELL_SIZE - 2),
                                   (GRID_X_OFFSET + x * CELL_SIZE + CELL_SIZE - 2, GRID_Y_OFFSET + y * CELL_SIZE + CELL_SIZE - 2), 2)
                                     
        # Draw ghost piece
        if self.upgrades['ghost_piece'] and self.current_piece:
            ghost_piece = Tetromino(self.current_piece.shape_index, self.current_piece.x, self.current_piece.y)
            ghost_piece.shape = self.current_piece.shape
            
            while not self.check_collision(0, 1, ghost_piece):
                ghost_piece.y += 1
                
            for x, y in ghost_piece.get_cells():
                if y >= 0:
                    pygame.draw.rect(self.screen, (100, 100, 100),
                                    (GRID_X_OFFSET + x * CELL_SIZE, GRID_Y_OFFSET + y * CELL_SIZE,
                                     CELL_SIZE - 2, CELL_SIZE - 2), 1)
                                     
        # Draw current piece with 3D effect
        if self.current_piece:
            color = RED if self.current_piece.is_bomb else self.current_piece.color
            for x, y in self.current_piece.get_cells():
                if y >= 0:
                    # Main block
                    pygame.draw.rect(self.screen, color,
                                    (GRID_X_OFFSET + x * CELL_SIZE, GRID_Y_OFFSET + y * CELL_SIZE,
                                     CELL_SIZE - 2, CELL_SIZE - 2))
                    # Highlight
                    highlight_color = tuple(min(255, c + 50) for c in color)
                    pygame.draw.line(self.screen, highlight_color,
                                   (GRID_X_OFFSET + x * CELL_SIZE, GRID_Y_OFFSET + y * CELL_SIZE),
                                   (GRID_X_OFFSET + x * CELL_SIZE + CELL_SIZE - 2, GRID_Y_OFFSET + y * CELL_SIZE), 2)
                    pygame.draw.line(self.screen, highlight_color,
                                   (GRID_X_OFFSET + x * CELL_SIZE, GRID_Y_OFFSET + y * CELL_SIZE),
                                   (GRID_X_OFFSET + x * CELL_SIZE, GRID_Y_OFFSET + y * CELL_SIZE + CELL_SIZE - 2), 2)
                    # Shadow
                    shadow_color = tuple(max(0, c - 50) for c in color)
                    pygame.draw.line(self.screen, shadow_color,
                                   (GRID_X_OFFSET + x * CELL_SIZE + CELL_SIZE - 2, GRID_Y_OFFSET + y * CELL_SIZE),
                                   (GRID_X_OFFSET + x * CELL_SIZE + CELL_SIZE - 2, GRID_Y_OFFSET + y * CELL_SIZE + CELL_SIZE - 2), 2)
                    pygame.draw.line(self.screen, shadow_color,
                                   (GRID_X_OFFSET + x * CELL_SIZE, GRID_Y_OFFSET + y * CELL_SIZE + CELL_SIZE - 2),
                                   (GRID_X_OFFSET + x * CELL_SIZE + CELL_SIZE - 2, GRID_Y_OFFSET + y * CELL_SIZE + CELL_SIZE - 2), 2)
                                     
        # Draw side panel background
        panel_width = SCREEN_WIDTH - (GRID_X_OFFSET + GRID_WIDTH * CELL_SIZE + 50)
        pygame.draw.rect(self.screen, (30, 30, 40), 
                        (GRID_X_OFFSET + GRID_WIDTH * CELL_SIZE + 30, 50, 
                         panel_width, SCREEN_HEIGHT - 100))
        pygame.draw.rect(self.screen, (60, 60, 80), 
                        (GRID_X_OFFSET + GRID_WIDTH * CELL_SIZE + 30, 50, 
                         panel_width, SCREEN_HEIGHT - 100), 3)
        
        # Draw held piece
        if self.upgrades['hold_piece'] and self.held_piece is not None:
            held_text = self.font.render("HOLD:", True, WHITE)
            self.screen.blit(held_text, (GRID_X_OFFSET + GRID_WIDTH * CELL_SIZE + 50, 100))
            
            held_shape = SHAPES[self.held_piece]
            held_color = SHAPE_COLORS[self.held_piece]
            
            for row_idx, row in enumerate(held_shape):
                for col_idx, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(self.screen, held_color,
                                        (GRID_X_OFFSET + GRID_WIDTH * CELL_SIZE + 50 + col_idx * 25, 
                                         130 + row_idx * 25, 23, 23))
                                         
        # Draw next piece
        next_text = self.font.render("NEXT:", True, WHITE)
        self.screen.blit(next_text, (GRID_X_OFFSET + GRID_WIDTH * CELL_SIZE + 50, 220))
        
        if self.next_piece_index is not None:
            next_shape = SHAPES[self.next_piece_index]
            next_color = SHAPE_COLORS[self.next_piece_index]
            
            for row_idx, row in enumerate(next_shape):
                for col_idx, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(self.screen, next_color,
                                        (GRID_X_OFFSET + GRID_WIDTH * CELL_SIZE + 50 + col_idx * 25, 
                                         250 + row_idx * 25, 23, 23))
                                         
        # Draw game info
        info_x = GRID_X_OFFSET + GRID_WIDTH * CELL_SIZE + 50
        info_y = 350
        
        # Draw info box
        pygame.draw.rect(self.screen, (40, 40, 50), 
                        (info_x - 10, info_y - 10, 250, 300))
        pygame.draw.rect(self.screen, (70, 70, 90), 
                        (info_x - 10, info_y - 10, 250, 300), 2)
        
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (info_x, info_y))
        
        level_text = self.font.render(f"Level: {self.level}", True, WHITE)
        self.screen.blit(level_text, (info_x, info_y + 35))
        
        lines_text = self.font.render(f"Lines: {self.lines_cleared}", True, WHITE)
        self.screen.blit(lines_text, (info_x, info_y + 70))
        
        round_text = self.font.render(f"Round: {self.round_number}", True, WHITE)
        self.screen.blit(round_text, (info_x, info_y + 105))
        
        target_text = self.font.render(f"Target: {self.round_target}", True, WHITE)
        self.screen.blit(target_text, (info_x, info_y + 140))
        
        money_text = self.font.render(f"Money: ${self.money}", True, YELLOW)
        self.screen.blit(money_text, (info_x, info_y + 175))
        
        # Draw deck info
        deck_text = self.font.render("DECK COMPOSITION:", True, WHITE)
        self.screen.blit(deck_text, (info_x, info_y + 220))
        
        # Draw deck pieces visually
        deck_y = info_y + 250
        deck_counter = Counter(self.piece_deck)
        
        for shape_idx, count in deck_counter.items():
            if count > 0:
                # Draw piece preview
                shape = SHAPES[shape_idx]
                color = SHAPE_COLORS[shape_idx]
                
                # Draw mini version of the piece
                mini_cell_size = 15
                for row_idx, row in enumerate(shape):
                    for col_idx, cell in enumerate(row):
                        if cell:
                            pygame.draw.rect(self.screen, color,
                                            (info_x + col_idx * mini_cell_size, 
                                             deck_y + row_idx * mini_cell_size,
                                             mini_cell_size - 1, mini_cell_size - 1))
                
                # Draw count
                count_text = self.font.render(f"x{count}", True, WHITE)
                self.screen.blit(count_text, (info_x + 80, deck_y + 5))
                
                # Draw piece name
                name_text = self.small_font.render(SHAPE_NAMES[shape_idx], True, WHITE)
                self.screen.blit(name_text, (info_x + 120, deck_y + 5))
                
                deck_y += 40
            
        # Draw jokers
        if self.jokers:
            joker_text = self.font.render("JOKERS:", True, GREEN)
            self.screen.blit(joker_text, (info_x, deck_y + 20))
            
            for i, joker in enumerate(self.jokers):
                joker_name = self.small_font.render(joker, True, GREEN)
                self.screen.blit(joker_name, (info_x, deck_y + 50 + i * 20))
                
    def draw_menu(self):
        # Clear screen
        self.screen.fill(BLACK)
        
        # Animated background
        self.menu_animation_time += 0.01
        for y in range(0, SCREEN_HEIGHT, 20):
            color_value = int(20 + 10 * math.sin(self.menu_animation_time + y * 0.01))
            color = (color_value, color_value, color_value + 5)
            pygame.draw.rect(self.screen, color, (0, y, SCREEN_WIDTH, 20))
        
        # Title
        title = self.title_font.render("TETRIS: BALATRO EDITION", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        self.screen.blit(title, title_rect)
        
        # Animated subtitle
        pulse = abs(math.sin(self.menu_animation_time * 2))
        subtitle_color = (int(100 + 155 * pulse), int(100 + 155 * pulse), 255)
        subtitle = self.large_font.render("Press SPACE to Start", True, subtitle_color)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Instructions
        instructions = [
            "Arrow Keys: Move/Rotate",
            "Space: Hard Drop",
            "C: Hold Piece",
            "ESC: Quit"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.font.render(instruction, True, WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 3 // 4 + i * 40))
            self.screen.blit(text, text_rect)
            
    def draw_shop(self):
        # Clear screen
        self.screen.fill(BLACK)
        
        # Background with subtle gradient
        for y in range(SCREEN_HEIGHT):
            color_value = 20 + int(10 * math.sin(y * 0.01))
            color = (color_value, color_value, color_value + 10)
            pygame.draw.line(self.screen, color, (0, y), (SCREEN_WIDTH, y))
        
        # Shop title
        title = self.large_font.render("SHOP - UPGRADE YOUR TETRIS", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title, title_rect)
        
        # Player money with coin icon
        money_text = self.large_font.render(f"${self.money}", True, YELLOW)
        money_rect = money_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(money_text, money_rect)
        
        # Draw coin icon
        pygame.draw.circle(self.screen, YELLOW, (money_rect.left - 30, money_rect.centery), 15)
        pygame.draw.circle(self.screen, GOLD, (money_rect.left - 30, money_rect.centery), 12)
        
        # Create three columns for shop sections
        col1_x = SCREEN_WIDTH // 6
        col2_x = SCREEN_WIDTH // 2
        col3_x = SCREEN_WIDTH * 5 // 6
        
        # Upgrades section (Column 1)
        upgrades_y = 180
        upgrades_text = self.medium_font.render("UPGRADES", True, WHITE)
        upgrades_rect = upgrades_text.get_rect(center=(col1_x, upgrades_y))
        self.screen.blit(upgrades_text, upgrades_rect)
        
        upgrades = [
            ("Score Multiplier +0.5", 200, 'score_multiplier', 0.5),
            ("Extra Line Bonus", 150, 'extra_lines', 1),
            ("Hold Piece", 300, 'hold_piece', True),
            ("Ghost Piece", 250, 'ghost_piece', True),
            ("Bomb Pieces (10% chance)", 400, 'bomb_piece', True)
        ]
        
        for i, (name, cost, key, value) in enumerate(upgrades):
            y_pos = upgrades_y + 50 + i * 60
            
            # Check if already owned
            if key in ['hold_piece', 'ghost_piece', 'bomb_piece'] and self.upgrades[key]:
                # Draw owned button
                button_rect = pygame.Rect(col1_x - 150, y_pos, 300, 50)
                pygame.draw.rect(self.screen, GREEN, button_rect)
                pygame.draw.rect(self.screen, (0, 200, 0), button_rect, 3)
                
                owned_text = self.font.render(f"{name} - OWNED", True, BLACK)
                owned_rect = owned_text.get_rect(center=button_rect.center)
                self.screen.blit(owned_text, owned_rect)
            else:
                # Draw upgrade button
                button_rect = pygame.Rect(col1_x - 150, y_pos, 300, 50)
                button_color = BLUE if self.money >= cost else GRAY
                pygame.draw.rect(self.screen, button_color, button_rect)
                pygame.draw.rect(self.screen, (0, 0, 200) if self.money >= cost else (100, 100, 100), button_rect, 3)
                
                upgrade_text = self.font.render(f"{name} - ${cost}", True, WHITE)
                upgrade_rect = upgrade_text.get_rect(center=button_rect.center)
                self.screen.blit(upgrade_text, upgrade_rect)
                
                # Check for click
                if pygame.mouse.get_pressed()[0] and button_rect.collidepoint(pygame.mouse.get_pos()):
                    if self.money >= cost:
                        self.money -= cost
                        if key == 'score_multiplier':
                            self.upgrades[key] += value
                        elif key == 'extra_lines':
                            self.upgrades[key] += value
                        else:
                            self.upgrades[key] = value
                            
        # Jokers section (Column 2)
        jokers_y = 180
        jokers_text = self.medium_font.render("JOKERS", True, GREEN)
        jokers_rect = jokers_text.get_rect(center=(col2_x, jokers_y))
        self.screen.blit(jokers_text, jokers_rect)
        
        jokers = [
            ("Double Points", 500, "Double Points"),
            ("Line Bonus", 300, "Line Bonus"),
            ("Level Boost", 400, "Level Boost")
        ]
        
        for i, (name, cost, joker_name) in enumerate(jokers):
            y_pos = jokers_y + 50 + i * 60
            
            # Check if already owned
            if joker_name in self.jokers:
                # Draw owned button
                button_rect = pygame.Rect(col2_x - 150, y_pos, 300, 50)
                pygame.draw.rect(self.screen, GREEN, button_rect)
                pygame.draw.rect(self.screen, (0, 200, 0), button_rect, 3)
                
                owned_text = self.font.render(f"{name} - OWNED", True, BLACK)
                owned_rect = owned_text.get_rect(center=button_rect.center)
                self.screen.blit(owned_text, owned_rect)
            else:
                # Draw joker button
                button_rect = pygame.Rect(col2_x - 150, y_pos, 300, 50)
                button_color = PURPLE if self.money >= cost else GRAY
                pygame.draw.rect(self.screen, button_color, button_rect)
                pygame.draw.rect(self.screen, (150, 0, 150) if self.money >= cost else (100, 100, 100), button_rect, 3)
                
                joker_text = self.font.render(f"{name} - ${cost}", True, WHITE)
                joker_rect = joker_text.get_rect(center=button_rect.center)
                self.screen.blit(joker_text, joker_rect)
                
                # Check for click
                if pygame.mouse.get_pressed()[0] and button_rect.collidepoint(pygame.mouse.get_pos()):
                    if self.money >= cost:
                        self.money -= cost
                        self.jokers.append(joker_name)
                        
        # Packs section (Column 3)
        packs_y = 180
        packs_text = self.medium_font.render("PACKS", True, GOLD)
        packs_rect = packs_text.get_rect(center=(col3_x, packs_y))
        self.screen.blit(packs_text, packs_rect)
        
        packs = [
            ("Basic Pack", 100, PackType.BASIC, "3 random pieces"),
            ("Premium Pack", 250, PackType.PREMIUM, "5 pieces, better odds"),
            ("Straight Pack", 200, PackType.STRAIGHT, "4 straight pieces")
        ]
        
        for i, (name, cost, pack_type, description) in enumerate(packs):
            y_pos = packs_y + 50 + i * 80
            
            # Draw pack button
            button_rect = pygame.Rect(col3_x - 150, y_pos, 300, 70)
            button_color = GOLD if self.money >= cost else GRAY
            pygame.draw.rect(self.screen, button_color, button_rect)
            pygame.draw.rect(self.screen, (200, 170, 0) if self.money >= cost else (100, 100, 100), button_rect, 3)
            
            pack_text = self.font.render(f"{name} - ${cost}", True, BLACK)
            pack_rect = pack_text.get_rect(center=(button_rect.centerx, button_rect.centery - 15))
            self.screen.blit(pack_text, pack_rect)
            
            desc_text = self.small_font.render(description, True, BLACK)
            desc_rect = desc_text.get_rect(center=(button_rect.centerx, button_rect.centery + 15))
            self.screen.blit(desc_text, desc_rect)
            
            # Check for click
            if pygame.mouse.get_pressed()[0] and button_rect.collidepoint(pygame.mouse.get_pos()):
                if self.money >= cost:
                    self.money -= cost
                    self.open_pack(pack_type)
                    
        # Continue button
        continue_rect = pygame.Rect(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 100, 300, 60)
        pygame.draw.rect(self.screen, GREEN, continue_rect)
        pygame.draw.rect(self.screen, (0, 200, 0), continue_rect, 3)
        
        continue_text = self.large_font.render("CONTINUE", True, BLACK)
        continue_text_rect = continue_text.get_rect(center=continue_rect.center)
        self.screen.blit(continue_text, continue_text_rect)
        
        # Check for continue click
        if pygame.mouse.get_pressed()[0] and continue_rect.collidepoint(pygame.mouse.get_pos()):
            self.start_next_round()
            
    def open_pack(self, pack_type):
        self.pack_type = pack_type
        self.pack_contents = []
        self.pack_opening_animation_time = 0
        
        if pack_type == PackType.BASIC:
            # Basic pack: 3 random pieces
            for _ in range(3):
                self.pack_contents.append(random.randint(0, len(SHAPES) - 1))
        elif pack_type == PackType.PREMIUM:
            # Premium pack: 5 pieces with better odds for straight pieces
            for _ in range(5):
                # 40% chance for straight piece, 60% for random
                if random.random() < 0.4:
                    self.pack_contents.append(0)  # Straight piece
                else:
                    self.pack_contents.append(random.randint(0, len(SHAPES) - 1))
        elif pack_type == PackType.STRAIGHT:
            # Straight pack: 4 straight pieces
            for _ in range(4):
                self.pack_contents.append(0)  # Straight piece
                
        self.state = GameState.PACK_OPENING
        
    def draw_pack_opening(self):
        # Clear screen
        self.screen.fill(BLACK)
        
        # Background with animation
        for y in range(SCREEN_HEIGHT):
            color_value = 20 + int(10 * math.sin(y * 0.01 + self.pack_opening_animation_time * 0.005))
            color = (color_value, color_value, color_value + 10)
            pygame.draw.line(self.screen, color, (0, y), (SCREEN_WIDTH, y))
        
        # Pack opening title
        title = self.large_font.render("PACK OPENING", True, GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title, title_rect)
        
        # Pack type
        pack_type_text = ""
        if self.pack_type == PackType.BASIC:
            pack_type_text = "Basic Pack"
        elif self.pack_type == PackType.PREMIUM:
            pack_type_text = "Premium Pack"
        elif self.pack_type == PackType.STRAIGHT:
            pack_type_text = "Straight Pack"
            
        pack_type = self.medium_font.render(pack_type_text, True, WHITE)
        pack_type_rect = pack_type.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(pack_type, pack_type_rect)
        
        # Draw pack contents with animation
        animation_progress = min(1.0, self.pack_opening_animation_time / 2000)  # 2 seconds animation
        
        # Calculate positions for pack contents
        content_width = 120
        spacing = 20
        total_width = len(self.pack_contents) * content_width + (len(self.pack_contents) - 1) * spacing
        start_x = (SCREEN_WIDTH - total_width) // 2
        y_pos = SCREEN_HEIGHT // 2 - 60
        
        # Draw each piece in the pack
        for i, shape_idx in enumerate(self.pack_contents):
            x_pos = start_x + i * (content_width + spacing)
            
            # Animate reveal
            if animation_progress > i / len(self.pack_contents):
                reveal_progress = min(1.0, (animation_progress - i / len(self.pack_contents)) * len(self.pack_contents))
                
                # Draw card background
                card_rect = pygame.Rect(x_pos, y_pos, content_width, 120)
                
                # Card flip animation
                if reveal_progress < 0.5:
                    # First half of flip: show back of card
                    scale = 1.0 - (reveal_progress * 2)
                    card_width = int(content_width * scale)
                    card_x = x_pos + (content_width - card_width) // 2
                    
                    pygame.draw.rect(self.screen, BLUE, (card_x, y_pos, card_width, 120))
                    pygame.draw.rect(self.screen, (0, 0, 150), (card_x, y_pos, card_width, 120), 3)
                    
                    # Draw question mark
                    if card_width > 20:
                        q_text = self.large_font.render("?", True, WHITE)
                        q_rect = q_text.get_rect(center=(card_x + card_width // 2, y_pos + 60))
                        self.screen.blit(q_text, q_rect)
                else:
                    # Second half of flip: show front of card
                    scale = (reveal_progress - 0.5) * 2
                    card_width = int(content_width * scale)
                    card_x = x_pos + (content_width - card_width) // 2
                    
                    # Card background
                    pygame.draw.rect(self.screen, WHITE, (card_x, y_pos, card_width, 120))
                    pygame.draw.rect(self.screen, (200, 200, 200), (card_x, y_pos, card_width, 120), 3)
                    
                    # Draw piece
                    if card_width > 40:
                        shape = SHAPES[shape_idx]
                        color = SHAPE_COLORS[shape_idx]
                        
                        # Calculate piece size and position
                        piece_size = min(card_width - 20, 80)
                        piece_x = card_x + (card_width - piece_size) // 2
                        piece_y = y_pos + 20
                        
                        # Draw piece cells
                        cell_size = piece_size // max(len(shape), len(shape[0]))
                        
                        for row_idx, row in enumerate(shape):
                            for col_idx, cell in enumerate(row):
                                if cell:
                                    pygame.draw.rect(self.screen, color,
                                                    (piece_x + col_idx * cell_size, 
                                                     piece_y + row_idx * cell_size,
                                                     cell_size - 1, cell_size - 1))
                        
                        # Draw piece name
                        name_text = self.small_font.render(SHAPE_NAMES[shape_idx], True, BLACK)
                        name_rect = name_text.get_rect(center=(card_x + card_width // 2, y_pos + 100))
                        self.screen.blit(name_text, name_rect)
        
        # Add to deck button (appears after animation)
        if animation_progress >= 1.0:
            button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 150, 300, 60)
            pygame.draw.rect(self.screen, GREEN, button_rect)
            pygame.draw.rect(self.screen, (0, 200, 0), button_rect, 3)
            
            button_text = self.large_font.render("ADD TO DECK", True, BLACK)
            button_text_rect = button_text.get_rect(center=button_rect.center)
            self.screen.blit(button_text, button_text_rect)
            
            # Check for click
            if pygame.mouse.get_pressed()[0] and button_rect.collidepoint(pygame.mouse.get_pos()):
                # Add all pieces to deck
                self.piece_deck.extend(self.pack_contents)
                self.state = GameState.SHOP
                
    def start_next_round(self):
        self.round_number += 1
        self.round_target = 1000 * self.round_number
        self.score = 0
        self.lines_cleared = 0
        self.level = 1
        self.fall_speed = 500
        
        # Apply Level Boost joker
        if "Level Boost" in self.jokers:
            self.level += 2
            self.fall_speed = max(100, self.fall_speed - 100)
            
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.next_piece_index = self.get_random_piece_from_deck()
        self.spawn_piece()
        self.state = GameState.PLAYING
        
    def draw_game_over(self):
        # Clear screen
        self.screen.fill(BLACK)
        
        # Background with subtle animation
        for y in range(SCREEN_HEIGHT):
            color_value = int(20 + 5 * math.sin(y * 0.01))
            color = (color_value, color_value, color_value)
            pygame.draw.line(self.screen, color, (0, y), (SCREEN_WIDTH, y))
        
        # Game over text
        game_over_text = self.title_font.render("GAME OVER", True, RED)
        game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        self.screen.blit(game_over_text, game_over_rect)
        
        # Score
        score_text = self.large_font.render(f"Final Score: {self.score}", True, WHITE)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(score_text, score_rect)
        
        # Restart and quit instructions
        restart_text = self.font.render("Press SPACE to restart or ESC to quit", True, WHITE)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 2 // 3))
        self.screen.blit(restart_text, restart_rect)
        
    def run(self):
        running = True
        dt = 0
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
                if event.type == pygame.KEYDOWN:
                    if self.state == GameState.MENU:
                        if event.key == pygame.K_SPACE:
                            # Initialize game properly
                            self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
                            self.next_piece_index = self.get_random_piece_from_deck()
                            self.spawn_piece()
                            self.state = GameState.PLAYING
                        elif event.key == pygame.K_ESCAPE:
                            running = False
                            
                    elif self.state == GameState.PLAYING:
                        if event.key == pygame.K_LEFT:
                            self.move(-1, 0)
                        elif event.key == pygame.K_RIGHT:
                            self.move(1, 0)
                        elif event.key == pygame.K_DOWN:
                            self.move(0, 1)
                        elif event.key == pygame.K_UP:
                            self.rotate_piece()
                        elif event.key == pygame.K_SPACE:
                            self.hard_drop()
                        elif event.key == pygame.K_c:
                            self.hold_piece()
                        # Removed ESC to shop access during gameplay
                            
                    elif self.state == GameState.SHOP:
                        if event.key == pygame.K_ESCAPE:
                            self.state = GameState.PLAYING
                            
                    elif self.state == GameState.PACK_OPENING:
                        if event.key == pygame.K_ESCAPE:
                            self.state = GameState.SHOP
                            
                    elif self.state == GameState.GAME_OVER:
                        if event.key == pygame.K_SPACE:
                            self.reset_game()
                        elif event.key == pygame.K_ESCAPE:
                            running = False
                            
            # Update
            self.update(dt)
            
            # Draw
            if self.state == GameState.MENU:
                self.draw_menu()
            elif self.state == GameState.PLAYING:
                self.draw_grid()
            elif self.state == GameState.SHOP:
                self.draw_shop()
            elif self.state == GameState.PACK_OPENING:
                self.draw_pack_opening()
            elif self.state == GameState.GAME_OVER:
                self.draw_game_over()
                
            pygame.display.flip()
            dt = self.clock.tick(60)
            
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = TetrisGame()
    game.run()