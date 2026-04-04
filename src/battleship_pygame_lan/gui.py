import os

import pygame

from .logic.enums import FieldState

CELL_SIZE = 40
MARGIN = 2
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (70, 70, 70)
BLUE_WATER = (30, 30, 60)
SHIP_COLOR = (100, 100, 100)
MISS_COLOR = (150, 150, 255)
HIT_COLOR = (255, 50, 50)
HOVER_COLOR = (0, 120, 215)
BUTTON_BG = (20, 20, 30, 220)


class MainMenu:
    def __init__(self, screen):
        self.screen = screen
        self.screen_rect = screen.get_rect()

        self.font_title = pygame.font.SysFont("Arial", 80, bold=True)
        self.font_button = pygame.font.SysFont("Arial", 38)
        self.font_label = pygame.font.SysFont("Arial", 28)

        self.bg_filenames = ["bg1.jpg", "bg2.jpg", "bg3.jpg"]
        self.backgrounds = []
        self.play_bg = None
        self.load_assets()

        self.current_idx = 0
        self.next_idx = 1
        self.alpha = 0
        self.fade_speed = 4
        self.display_time = 20000
        self.last_switch = pygame.time.get_ticks()
        self.is_fading = False

        self.menu_state = "MAIN"
        self.last_state = "MAIN"
        self.panel_y = -self.screen_rect.height
        self.slide_speed = 25

        self.player_name = "Gamer"
        self.host_ip = "127.0.0.1"
        self.input_active = False
        self.input_field_rect = pygame.Rect(0, 0, 0, 0)

        self.left_margin = 70
        self.main_buttons = [
            {"text": "Play", "pos_y": 240, "action": "show_modes"},
            {"text": "Settings", "pos_y": 330, "action": "show_settings"},
            {"text": "Exit", "pos_y": 420, "action": "quit"},
        ]

        self.mode_buttons = [
            {"text": "Host Game", "pos_y": 240, "action": "host"},
            {"text": "Join Game", "pos_y": 330, "action": "show_join_input"},
            {"text": "Back", "pos_y": 420, "action": "back"},
        ]

        self.settings_buttons = [
            {"text": "Save & Back", "pos_y": 420, "action": "back"},
        ]

        self.join_buttons = [
            {"text": "Connect", "pos_y": 360, "action": "join_final"},
            {"text": "Back", "pos_y": 440, "action": "show_modes"},
        ]

    def load_assets(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(base_dir, "..", ".."))
        assets_path = os.path.join(project_root, "assets")

        for name in self.bg_filenames:
            path = os.path.join(assets_path, name)
            self.backgrounds.append(self._load_and_scale(path))

        play_path = os.path.join(assets_path, "play_background.jpg")
        self.play_bg = self._load_and_scale(play_path)

    def _load_and_scale(self, path):
        try:
            img = pygame.image.load(path).convert()
            return pygame.transform.scale(
                img, (self.screen_rect.width, self.screen_rect.height)
            )
        except:
            surf = pygame.Surface(self.screen_rect.size)
            surf.fill((30, 30, 30))
            return surf

    def update(self):
        now = pygame.time.get_ticks()
        if not self.is_fading and now - self.last_switch > self.display_time:
            self.is_fading = True
            self.alpha = 0
        if self.is_fading:
            self.alpha += self.fade_speed
            if self.alpha >= 255:
                self.alpha = 255
                self.is_fading = False
                self.current_idx = self.next_idx
                self.next_idx = (self.current_idx + 1) % len(self.backgrounds)
                self.last_switch = now

        target_y = (
            0
            if self.menu_state in ["MODE", "SETTINGS", "JOIN_INPUT"]
            else -self.screen_rect.height
        )
        if self.panel_y < target_y:
            self.panel_y = min(self.panel_y + self.slide_speed, target_y)
        elif self.panel_y > target_y:
            self.panel_y = max(self.panel_y - self.slide_speed, target_y)

    def draw(self):
        self.update()
        self.screen.blit(self.backgrounds[self.current_idx], (0, 0))
        if self.is_fading:
            next_bg = self.backgrounds[self.next_idx].copy()
            next_bg.set_alpha(self.alpha)
            self.screen.blit(next_bg, (0, 0))

        if self.panel_y > -self.screen_rect.height:
            active_view = (
                self.menu_state if self.menu_state != "MAIN" else self.last_state
            )
            if active_view in ["MODE", "JOIN_INPUT"]:
                if self.play_bg:
                    self.screen.blit(self.play_bg, (0, self.panel_y))
            elif active_view == "SETTINGS":
                overlay = pygame.Surface(self.screen_rect.size, pygame.SRCALPHA)
                overlay.fill((10, 10, 20, 220))
                self.screen.blit(overlay, (0, self.panel_y))

        mouse_pos = pygame.mouse.get_pos()

        if self.menu_state == "MAIN" and self.panel_y <= -self.screen_rect.height:
            title_surf = self.font_title.render("Battleship LAN", True, WHITE)
            self.screen.blit(title_surf, (self.left_margin, 80))
            self._draw_buttons(self.main_buttons, mouse_pos)
        else:
            active_view = (
                self.menu_state if self.menu_state != "MAIN" else self.last_state
            )
            if active_view == "MODE":
                self._draw_buttons(self.mode_buttons, mouse_pos, True, self.panel_y)
            elif active_view == "SETTINGS":
                self._draw_input_content(
                    "Username:", self.player_name, mouse_pos, self.panel_y
                )
                self._draw_buttons(self.settings_buttons, mouse_pos, True, self.panel_y)
            elif active_view == "JOIN_INPUT":
                self._draw_input_content(
                    "HOST IP:", self.host_ip, mouse_pos, self.panel_y
                )
                self._draw_buttons(self.join_buttons, mouse_pos, True, self.panel_y)

    def _draw_input_content(self, label_text, value_text, mouse_pos, offset_y):
        label = self.font_label.render(label_text, True, WHITE)
        self.screen.blit(
            label, label.get_rect(centerx=self.screen_rect.centerx, top=180 + offset_y)
        )

        input_rect = pygame.Rect(0, 0, 360, 55)
        input_rect.center = (self.screen_rect.centerx, 250 + offset_y)
        pygame.draw.rect(self.screen, (20, 20, 30), input_rect)
        pygame.draw.rect(
            self.screen, HOVER_COLOR if self.input_active else WHITE, input_rect, 2
        )

        txt_surf = self.font_button.render(value_text, True, WHITE)
        self.screen.blit(txt_surf, txt_surf.get_rect(center=input_rect.center))
        self.input_field_rect = input_rect

    def _draw_buttons(self, button_list, mouse_pos, is_centered=False, offset_y=0):
        for btn in button_list:
            rect = pygame.Rect(0, 0, 280, 65)
            if is_centered:
                rect.centerx, rect.y = self.screen_rect.centerx, btn["pos_y"] + offset_y
            else:
                rect.x, rect.y = self.left_margin, btn["pos_y"]

            if rect.bottom < 0 or rect.top > self.screen_rect.height:
                continue
            is_hov = rect.collidepoint(mouse_pos)
            btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            btn_surf.fill(BUTTON_BG)
            self.screen.blit(btn_surf, rect.topleft)
            pygame.draw.rect(self.screen, HOVER_COLOR if is_hov else WHITE, rect, 2)
            txt = self.font_button.render(
                btn["text"], True, HOVER_COLOR if is_hov else WHITE
            )
            self.screen.blit(txt, txt.get_rect(center=rect.center))
            btn["rect"] = rect

    def handle_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.menu_state in ["SETTINGS", "JOIN_INPUT"]:
                self.input_active = self.input_field_rect.collidepoint(event.pos)

            btns = []
            if self.menu_state == "MAIN":
                btns = self.main_buttons
            elif self.menu_state == "MODE":
                btns = self.mode_buttons
            elif self.menu_state == "SETTINGS":
                btns = self.settings_buttons
            elif self.menu_state == "JOIN_INPUT":
                btns = self.join_buttons

            for btn in btns:
                if "rect" in btn and btn["rect"].collidepoint(event.pos):
                    self.last_state = self.menu_state
                    if btn["action"] == "show_modes":
                        self.menu_state = "MODE"
                        return None
                    elif btn["action"] == "show_settings":
                        self.menu_state = "SETTINGS"
                        return None
                    elif btn["action"] == "show_join_input":
                        self.menu_state = "JOIN_INPUT"
                        return None
                    elif btn["action"] == "back":
                        self.menu_state = "MAIN"
                        return "settings_updated"
                    return btn["action"]

        if event.type == pygame.KEYDOWN and self.input_active:
            target_attr = "player_name" if self.menu_state == "SETTINGS" else "host_ip"
            val = getattr(self, target_attr)

            if event.key == pygame.K_BACKSPACE:
                setattr(self, target_attr, val[:-1])
            elif event.key == pygame.K_RETURN:
                self.input_active = False
            else:
                if len(val) < 20:
                    setattr(self, target_attr, val + event.unicode)
        return None


class BoardRenderer:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 18)
        self.colors = {
            FieldState.Empty: BLUE_WATER,
            FieldState.Taken: SHIP_COLOR,
            FieldState.Missed: MISS_COLOR,
            FieldState.Hit: HIT_COLOR,
        }

    def draw(self, board, offset_x, offset_y, title):
        title_surf = pygame.font.SysFont("Arial", 24, bold=True).render(
            title, True, WHITE
        )
        self.screen.blit(title_surf, (offset_x, offset_y - 40))
        for r in range(board.row):
            self.screen.blit(
                self.font.render(str(r), True, WHITE),
                (offset_x - 25, offset_y + r * 42 + 10),
            )
            for c in range(board.column):
                if r == 0:
                    self.screen.blit(
                        self.font.render(str(c), True, WHITE),
                        (offset_x + c * 42 + 15, offset_y - 20),
                    )
                rect = pygame.Rect(offset_x + c * 42, offset_y + r * 42, 40, 40)
                pygame.draw.rect(
                    self.screen,
                    self.colors.get(board.get_field_state(r, c), BLUE_WATER),
                    rect,
                )
                pygame.draw.rect(self.screen, GRAY, rect, 1)

    def get_clicked_cell(self, pos, ox, oy):
        col, row = (pos[0] - ox) // 42, (pos[1] - oy) // 42
        return (int(row), int(col)) if 0 <= row < 10 and 0 <= col < 10 else None
