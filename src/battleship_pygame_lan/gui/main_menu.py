import os
from typing import Any, cast

import pygame

from ..logic.enums import ShotResult

WHITE = (255, 255, 255)
GRAY = (70, 70, 70)
HOVER_COLOR = (0, 120, 215)
BUTTON_BG = (20, 20, 30, 220)


class MainMenu:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.screen_rect = screen.get_rect()

        self.font_title = pygame.font.SysFont("Arial", 80, bold=True)
        self.font_button = pygame.font.SysFont("Arial", 38)
        self.font_label = pygame.font.SysFont("Arial", 28)

        self.bg_filenames = ["bg1.jpg", "bg2.jpg", "bg3.jpg"]
        self.backgrounds: list[pygame.Surface] = []
        self.play_bg: pygame.Surface | None = None
        self.click_sound: pygame.mixer.Sound | None = None
        self.play_sound: pygame.mixer.Sound | None = None
        self.hit_sound: pygame.mixer.Sound | None = None
        self.miss_sound: pygame.mixer.Sound | None = None
        self.volume: float = 0.5

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
        self.panel_y = float(-self.screen_rect.height)
        self.slide_speed = 25

        self.player_name = "Morbius"
        self.host_ip = "127.0.0.1"
        self.input_active = False
        self.input_field_rect = pygame.Rect(0, 0, 0, 0)
        self.slider_rect = pygame.Rect(0, 0, 300, 10)
        self.left_margin = 70

        self.main_buttons: list[dict[str, Any]] = [
            {"text": "Play", "pos_y": 240, "action": "show_modes"},
            {"text": "Settings", "pos_y": 330, "action": "show_settings"},
            {"text": "Exit", "pos_y": 420, "action": "quit"},
        ]
        self.mode_buttons: list[dict[str, Any]] = [
            {"text": "Host Game", "pos_y": 240, "action": "host"},
            {"text": "Join Game", "pos_y": 330, "action": "show_join_input"},
            {"text": "Back", "pos_y": 420, "action": "back"},
        ]
        self.settings_buttons: list[dict[str, Any]] = [
            {"text": "Save & Back", "pos_y": 450, "action": "back"}
        ]
        self.join_buttons: list[dict[str, Any]] = [
            {"text": "Connect", "pos_y": 360, "action": "join_final"},
            {"text": "Back", "pos_y": 440, "action": "show_modes"},
        ]

    def load_assets(self) -> None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(base_dir, "..", "..", ".."))
        gfx_path = os.path.join(project_root, "assets", "gfx")
        sfx_path = os.path.join(project_root, "assets", "sfx")

        self.backgrounds = [
            self._load_and_scale(os.path.join(gfx_path, f)) for f in self.bg_filenames
        ]
        self.play_bg = self._load_and_scale(
            os.path.join(gfx_path, "play_background.jpg")
        )

        try:
            click_file = os.path.join(sfx_path, "click.mp3")
            play_file = os.path.join(sfx_path, "play.mp3")
            hit_file = os.path.join(sfx_path, "hit.mp3")
            miss_file = os.path.join(sfx_path, "miss.mp3")

            if os.path.exists(click_file):
                self.click_sound = pygame.mixer.Sound(click_file)
            if os.path.exists(play_file):
                self.play_sound = pygame.mixer.Sound(play_file)
            if os.path.exists(hit_file):
                self.hit_sound = pygame.mixer.Sound(hit_file)
            if os.path.exists(miss_file):
                self.miss_sound = pygame.mixer.Sound(miss_file)

            self.update_sfx_volume()
        except Exception:
            pass

    def _load_and_scale(self, path: str) -> pygame.Surface:
        try:
            img = pygame.image.load(path).convert()
            return pygame.transform.scale(
                img, (self.screen_rect.width, self.screen_rect.height)
            )
        except Exception:
            surf = pygame.Surface(self.screen_rect.size)
            surf.fill((30, 30, 30))
            return surf

    def update_sfx_volume(self) -> None:
        for sound in [
            self.click_sound,
            self.play_sound,
            self.hit_sound,
            self.miss_sound,
        ]:
            if sound:
                sound.set_volume(self.volume)

    def play_combat_sound(self, result: ShotResult) -> None:
        if result in [ShotResult.Hit, ShotResult.Sunk]:
            if self.hit_sound:
                self.hit_sound.play()
        elif result == ShotResult.Miss and self.miss_sound:
            self.miss_sound.play()

    def update(self) -> None:
        now = pygame.time.get_ticks()
        if not self.is_fading and now - self.last_switch > self.display_time:
            self.is_fading, self.alpha = True, 0
        if self.is_fading:
            self.alpha += self.fade_speed
            if self.alpha >= 255:
                self.alpha, self.is_fading = 255, False
                self.current_idx = self.next_idx
                self.next_idx = (self.current_idx + 1) % len(self.backgrounds)
                self.last_switch = now

        target_y = (
            0.0
            if self.menu_state in ["MODE", "SETTINGS", "JOIN_INPUT"]
            else float(-self.screen_rect.height)
        )
        if self.panel_y < target_y:
            self.panel_y = min(self.panel_y + self.slide_speed, target_y)
        elif self.panel_y > target_y:
            self.panel_y = max(self.panel_y - self.slide_speed, target_y)

    def handle_events(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.menu_state == "SETTINGS" and self.slider_rect.collidepoint(
                event.pos
            ):
                self._update_volume(event.pos[0])

            btns: list[dict[str, Any]] = []
            if self.menu_state == "MAIN":
                btns = self.main_buttons
            elif self.menu_state == "MODE":
                btns = self.mode_buttons
            elif self.menu_state == "SETTINGS":
                btns = self.settings_buttons
            elif self.menu_state == "JOIN_INPUT":
                btns = self.join_buttons

            for btn in btns:
                if "rect" in btn and isinstance(btn["rect"], pygame.Rect):
                    if btn["rect"].collidepoint(event.pos):
                        if self.menu_state == "MAIN" and btn["text"] == "Play":
                            if self.play_sound:
                                self.play_sound.play()
                        elif self.click_sound:
                            self.click_sound.play()

                        self.last_state = self.menu_state
                        action = cast(str, btn["action"])
                        if action == "show_modes":
                            self.menu_state = "MODE"
                        elif action == "show_settings":
                            self.menu_state = "SETTINGS"
                        elif action == "show_join_input":
                            self.menu_state = "JOIN_INPUT"
                        elif action == "back":
                            self.menu_state = "MAIN"
                            return "settings_updated"
                        return action

        if (
            event.type == pygame.MOUSEMOTION
            and pygame.mouse.get_pressed()[0]
            and self.menu_state == "SETTINGS"
            and self.slider_rect.collidepoint(event.pos)
        ):
            self._update_volume(event.pos[0])

        return None

    def _update_volume(self, mouse_x: int) -> None:
        rel_x = max(0, min(mouse_x - self.slider_rect.left, self.slider_rect.width))
        self.volume = rel_x / self.slider_rect.width
        self.update_sfx_volume()

    def draw(self) -> None:
        self.update()
        self.screen.blit(self.backgrounds[self.current_idx], (0, 0))
        if self.is_fading:
            nxt = self.backgrounds[self.next_idx].copy()
            nxt.set_alpha(self.alpha)
            self.screen.blit(nxt, (0, 0))

        if self.panel_y > -self.screen_rect.height:
            active = self.menu_state if self.menu_state != "MAIN" else self.last_state
            if active == "SETTINGS":
                ov = pygame.Surface(self.screen_rect.size, pygame.SRCALPHA)
                ov.fill((10, 10, 20, 220))
                self.screen.blit(ov, (0, int(self.panel_y)))
            elif self.play_bg:
                self.screen.blit(self.play_bg, (0, int(self.panel_y)))

        m_pos = pygame.mouse.get_pos()
        if self.menu_state == "MAIN" and self.panel_y <= -self.screen_rect.height:
            self.screen.blit(
                self.font_title.render("Battleship LAN", True, WHITE),
                (self.left_margin, 80),
            )
            self._draw_buttons(self.main_buttons, m_pos)
        else:
            active = self.menu_state if self.menu_state != "MAIN" else self.last_state
            off_y = int(self.panel_y)
            if active == "MODE":
                self._draw_buttons(self.mode_buttons, m_pos, True, off_y)
            elif active == "SETTINGS":
                self._draw_settings_view(m_pos, off_y)
                self._draw_buttons(self.settings_buttons, m_pos, True, off_y)
            elif active == "JOIN_INPUT":
                self._draw_input_content("HOST IP:", self.host_ip, m_pos, off_y)
                self._draw_buttons(self.join_buttons, m_pos, True, off_y)

    def _draw_settings_view(self, m_pos: tuple[int, int], off_y: int) -> None:
        self._draw_input_content("PLAYER NAME:", self.player_name, m_pos, off_y, 150)
        self.screen.blit(
            self.font_label.render("VOLUME:", True, WHITE),
            (self.screen_rect.centerx - 50, 310 + off_y),
        )
        self.slider_rect.center = (self.screen_rect.centerx, 360 + off_y)
        pygame.draw.rect(self.screen, GRAY, self.slider_rect)
        hx = self.slider_rect.left + int(self.volume * self.slider_rect.width)
        pygame.draw.rect(
            self.screen, HOVER_COLOR, (hx - 7, self.slider_rect.y - 7, 15, 25)
        )

    def _draw_input_content(
        self, lbl: str, val: str, m_pos: tuple[int, int], off_y: int, top: int = 180
    ) -> None:
        self.screen.blit(
            self.font_label.render(lbl, True, WHITE),
            (self.screen_rect.centerx - 80, top + off_y),
        )
        rect = pygame.Rect(self.screen_rect.centerx - 180, top + 50 + off_y, 360, 55)
        pygame.draw.rect(self.screen, (20, 20, 30), rect)
        pygame.draw.rect(
            self.screen, HOVER_COLOR if rect.collidepoint(m_pos) else WHITE, rect, 2
        )
        txt = self.font_button.render(val, True, WHITE)
        self.screen.blit(txt, txt.get_rect(center=rect.center))
        self.input_field_rect = rect

    def _draw_buttons(
        self,
        b_list: list[dict[str, Any]],
        m_pos: tuple[int, int],
        center: bool = False,
        off_y: int = 0,
    ) -> None:
        for b in b_list:
            r = pygame.Rect(0, 0, 280, 65)
            if center:
                r.centerx, r.y = self.screen_rect.centerx, b["pos_y"] + off_y
            else:
                r.x, r.y = self.left_margin, b["pos_y"]

            hov = r.collidepoint(m_pos)
            s = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            s.fill(BUTTON_BG)
            self.screen.blit(s, r.topleft)
            pygame.draw.rect(self.screen, HOVER_COLOR if hov else WHITE, r, 2)
            t = self.font_button.render(b["text"], True, HOVER_COLOR if hov else WHITE)
            self.screen.blit(t, t.get_rect(center=r.center))
            b["rect"] = r
