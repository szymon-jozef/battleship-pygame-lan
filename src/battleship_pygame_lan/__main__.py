import logging
import socket
import sys
import threading
import time
from pathlib import Path
from queue import Empty

import pygame
from appdirs import user_log_dir

from battleship_pygame_lan.game_manager import GameManager
from battleship_pygame_lan.game_manager.enums import GuiEvent
from battleship_pygame_lan.gui.board_render import BoardRenderer
from battleship_pygame_lan.gui.main_menu import MainMenu
from battleship_pygame_lan.logic import ShipType
from battleship_pygame_lan.network import GameState
from battleship_pygame_lan.network.models import ReadyType
from battleship_pygame_lan.network.payloads import build_ready_payload
from battleship_pygame_lan.network.server import NetworkServer


def get_local_ip() -> str:
    """Pobiera lokalny adres IP hosta w sieci LAN."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return str(ip)
    except Exception:
        return "127.0.0.1"


def get_next_needed_ship(gm: GameManager) -> ShipType | None:
    """Zwraca kolejny typ statku, który gracz musi jeszcze rozstawić."""
    order: list[ShipType] = [
        ShipType.FourMaster,
        ShipType.ThreeMaster,
        ShipType.TwoMaster,
        ShipType.OneMaster,
    ]
    for ship_type in order:
        if gm.player.available_ships[ship_type] > 0:
            return ship_type
    return None


def draw_end_screen(
    screen: pygame.Surface,
    font_title: pygame.font.Font,
    font_stats: pygame.font.Font,
    winner_name: str,
    stats: dict,
) -> pygame.Rect:
    """Rysuje ekran końcowy ze statystykami i zwraca Rect przycisku powrotu."""
    screen.fill((15, 15, 35))

    title_text = f"GRACZ {winner_name.upper()} WYGRYWA!"
    title_surf = font_title.render(title_text, True, (255, 215, 0))
    title_rect = title_surf.get_rect(center=(500, 80))
    screen.blit(title_surf, title_rect)

    total_shots = stats["shots"]
    accuracy = (stats["hits"] / total_shots * 100) if total_shots > 0 else 0.0

    # Usunięto: f"Liczba zatopionych statków: {stats['sunk']}",
    stats_labels = [
        f"Liczba oddanych strzałów: {stats['shots']}",
        f"Liczba trafień: {stats['hits']}",
        f"Liczba pudeł: {stats['misses']}",
        f"Celność: {accuracy:.1f}%",
        f"Najdłuższa seria trafień: {stats['max_streak']}",
    ]

    start_y = 160
    for i, label in enumerate(stats_labels):
        surf = font_stats.render(label, True, (220, 220, 255))
        rect = surf.get_rect(center=(500, start_y + i * 40))
        screen.blit(surf, rect)

    # Przycisk powrotu do menu
    btn_rect = pygame.Rect(400, 480, 200, 50)
    pygame.draw.rect(screen, (40, 80, 150), btn_rect, border_radius=8)
    pygame.draw.rect(screen, (255, 255, 255), btn_rect, 2, border_radius=8)

    btn_text = font_stats.render("POWRÓT DO MENU", True, (255, 255, 255))
    btn_text_rect = btn_text.get_rect(center=btn_rect.center)
    screen.blit(btn_text, btn_text_rect)

    return btn_rect


def main() -> None:
    logger = logging.getLogger(__name__)
    log_dir: Path = Path(user_log_dir("battleship-pygame-lan"))
    log_fname: Path = Path("battleships.log")
    log_path: Path = log_dir.joinpath(log_fname)

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path.touch()

    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(console_handler)

    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((1000, 600))
    pygame.display.set_caption("Battleship LAN")
    clock = pygame.time.Clock()

    # --- ŁADOWANIE DŹWIĘKÓW MP3 ---
    try:
        hit_sound = pygame.mixer.Sound("assets/sfx/hit.ogg")
        miss_sound = pygame.mixer.Sound("assets/sfx/miss.ogg")
        print("[AUDIO] Pomyślnie załadowano dźwięki .ogg")
    except Exception as e:
        hit_sound = None
        miss_sound = None
        print(f"[MUTE] Brak plików dźwiękowych: {e}")

    info_font = pygame.font.SysFont("Arial", 22, bold=True)
    end_title_font = pygame.font.SysFont("Arial", 36, bold=True)
    end_stats_font = pygame.font.SysFont("Arial", 24, bold=False)

    menu = MainMenu(screen)
    renderer = BoardRenderer(screen)

    gm: GameManager | None = None
    server: NetworkServer | None = None
    current_host_ip = ""

    ready_sent = False
    valid_ready_type = ReadyType.SHIP_PLACED

    game_state = "MENU"
    running = True

    # Słownik przechowujący statystyki lokalnego gracza
    player_stats = {
        "shots": 0,
        "hits": 0,
        "misses": 0,
        "current_streak": 0,
        "max_streak": 0,
    }
    end_game_winner = ""

    # Kierunek stawiania statku (True = poziomo, False = pionowo)
    ship_horizontal = True

    while running:
        pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if game_state == "MENU":
                action = menu.handle_events(event)
                if action == "settings_updated" and gm is not None:
                    gm.player.name = menu.player_name

                elif action == "host":
                    current_host_ip = get_local_ip()
                    print(
                        f"\n[HOST] Uruchamianie serwera... Twoje IP: {current_host_ip}"
                    )

                    server = NetworkServer(server_ip="0.0.0.0")
                    server_thread = threading.Thread(target=server.start, daemon=True)
                    server_thread.start()

                    time.sleep(0.5)

                    print(
                        "[GM] Inicjalizacja hosta pod IP: 127.0.0.1 "
                        f"(Zewnętrznie: {current_host_ip})"
                    )
                    gm = GameManager(
                        player_name=menu.player_name, server_ip="127.0.0.1"
                    )
                    gm.connect()

                    ready_sent = False
                    # Reset statystyk przed nową grą
                    player_stats = {
                        "shots": 0,
                        "hits": 0,
                        "misses": 0,
                        "sunk": 0,
                        "current_streak": 0,
                        "max_streak": 0,
                    }
                    game_state = "GAME"

                elif action == "join_final":
                    target_ip = getattr(menu, "target_ip", "127.0.0.1")
                    print(f"\n[KLIENT] Łączenie z hostem: {target_ip}...")

                    gm = GameManager(player_name=menu.player_name, server_ip=target_ip)
                    try:
                        gm.connect()
                        ready_sent = False
                        # Reset statystyk przed nową grą
                        player_stats = {
                            "shots": 0,
                            "hits": 0,
                            "misses": 0,
                            "sunk": 0,
                            "current_streak": 0,
                            "max_streak": 0,
                        }
                        game_state = "GAME"
                    except Exception as e:
                        print(f"[BŁĄD] Połączenie nieudane: {e}")

                elif action == "quit":
                    running = False

            elif game_state == "END_SCREEN":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Sprawdzenie kliknięcia przycisku powrotu narysowanego przez draw_end_screen
                    btn_rect = draw_end_screen(
                        screen,
                        end_title_font,
                        end_stats_font,
                        end_game_winner,
                        player_stats,
                    )
                    if btn_rect.collidepoint(event.pos):
                        # Rozłączenie starej sesji, aby można było zagrać ponownie
                        if gm and gm.network_client:
                            gm.network_client.disconnect()
                        if server:
                            server.stop()
                            server = None
                        gm = None
                        game_state = "MENU"

            elif game_state == "GAME" and gm is not None:
                # Sprawdzamy, czy lokalny gracz wciąż jeszcze fizycznie rozstawia statki
                is_local_placement = (
                    gm.network_client.enemy_name is not None
                    and not gm.player.is_every_ship_placed
                )

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        game_state = "MENU"
                    elif event.key in (pygame.K_r, pygame.K_SPACE):
                        ship_horizontal = not ship_horizontal
                        print(
                            f"[GRA] Orientacja statku: "
                            f"{'POZIOMA' if ship_horizontal else 'PIONOWA'}"
                        )

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # 1. KLIKANIE W FAZIE ROZSTAWIANIA STATKÓW
                    if is_local_placement:
                        cell = renderer.get_clicked_cell(pos, 50, 80)
                        if cell:
                            row, col = cell
                            next_ship: ShipType | None = get_next_needed_ship(gm)
                            if next_ship:
                                try:
                                    success = gm.player.place_ship(
                                        next_ship, row, col, ship_horizontal
                                    )
                                    if success:
                                        print(
                                            "[GRA] Postawiono"
                                            f"{next_ship.name} na pozycji {row, col}"
                                        )
                                except Exception as e:
                                    print(f"[GRA] Nie można postawić statku: {e}")
                                    logger.error(f"Ship placement failed: {e}")

                    # 2. KLIKANIE W FAZIE STRZELANIA
                    elif (
                        gm.network_client.enemy_name
                        and gm.player.is_every_ship_placed
                        and gm.game_state != GameState.SHIP_PLACEMENT
                        and gm.network_client.is_my_turn
                    ):
                        cell = renderer.get_clicked_cell(pos, 550, 80)
                        if cell:
                            row, col = cell
                            try:
                                gm.player.name = gm.network_client.player_name
                                gm.shoot(row, col)
                            except Exception as e:
                                print(f"[GRA] Nie można oddać strzału: {e}")
                                logger.error(f"Błąd wysyłania ataku: {e}")

        # === OBSŁUGA SEKCJI SIECIOWEJ POPRZEZ MANAGER ===
        if game_state == "GAME" and gm and gm.network_client.connected:
            # Automatyczne wysłanie pakietu gotowości po rozstawieniu całej floty
            if (
                gm.network_client.enemy_name
                and gm.player.is_every_ship_placed
                and not ready_sent
            ):
                print(
                    "[GRA] Flota gotowa. "
                    f"Wysyłanie pakietu SHIP_PLACED dla: {gm.player.name}"
                )
                ready_payload = build_ready_payload(
                    gm.player.name, valid_ready_type, True
                )
                gm.network_client.send_to_socket(
                    gm.network_client.client, ready_payload
                )
                ready_sent = True

            gm.handle_response()

            # --- KONSUMOWANIE KOLEJKI GUI + DŹWIĘKI + STATYSTYKI ---
            try:
                while True:
                    gui_event = gm.gui_events_queue.get_nowait()
                    if gui_event == GuiEvent.ShotHit:
                        print("[GUI EVENT] Trafiony!")
                        if hit_sound:
                            hit_sound.play()

                        # Aktualizacja statystyk lokalnego gracza (strzały i trafienia)
                        player_stats["shots"] += 1
                        player_stats["hits"] += 1
                        player_stats["current_streak"] += 1
                        if player_stats["current_streak"] > player_stats["max_streak"]:
                            player_stats["max_streak"] = player_stats["current_streak"]

                    elif gui_event == GuiEvent.ShotMissed:
                        print("[GUI EVENT] Pudło!")
                        if miss_sound:
                            miss_sound.play()

                        # Aktualizacja statystyk lokalnego gracza (strzały i pudła)
                        player_stats["shots"] += 1
                        player_stats["misses"] += 1
                        player_stats["current_streak"] = 0

                    elif gui_event == GuiEvent.GameLost:
                        print("[GUI EVENT] Przegrana...")
                        end_game_winner = gm.network_client.enemy_name or "Przeciwnik"
                        game_state = "END_SCREEN"

                    elif gui_event == GuiEvent.GameWon:
                        print("[GUI EVENT] Wygrana!")
                        end_game_winner = menu.player_name
                        # Usunięto: player_stats["sunk"] = 10
                        game_state = "END_SCREEN"

                    gm.gui_events_queue.task_done()
            except Empty:
                pass

        # === RENDEROWANIE INTERFEJSU GRY ===
        if game_state == "MENU":
            menu.draw()
            ready_sent = False

        elif game_state == "END_SCREEN":
            draw_end_screen(
                screen, end_title_font, end_stats_font, end_game_winner, player_stats
            )

        elif game_state == "GAME" and gm is not None:
            screen.fill((10, 10, 25))

            is_local_placement = (
                gm.network_client.enemy_name is not None
                and not gm.player.is_every_ship_placed
            )

            # --- OBLICZANIE HOVERU DLA PODGLĄDU STATKU ---
            hover_cell = None
            hover_ship_info = None

            if is_local_placement:
                hover_cell = renderer.get_clicked_cell(pos, 50, 80)
                if hover_cell:
                    next_ship = get_next_needed_ship(gm)
                    if next_ship:
                        hover_ship_info = (next_ship.value, ship_horizontal)

            # Lewy ekran: Nasza flota
            renderer.draw(
                gm.player.board,
                50,
                80,
                f"FLEET: {gm.player.name}",
                hover_cell=hover_cell,
                hover_ship_info=hover_ship_info,
            )

            # Prawy ekran: Radar przeciwnika
            renderer.draw(
                gm.player.radar,
                550,
                80,
                f"RADAR (OPPONENT: {gm.network_client.enemy_name or 'Oczekiwanie...'})",
            )

            # --- SEKCJA STATUSÓW DOLNYCH ---
            if gm.network_client.connected:
                if not gm.network_client.enemy_name:
                    turn_text = "OCZEKIWANIE NA DRUGIEGO GRACZA..."
                    turn_color = (255, 255, 0)

                # Sytuacja 1: Ty wciąż rozstawiasz statki
                elif is_local_placement:
                    next_ship = get_next_needed_ship(gm)
                    if next_ship:
                        orient = "POZIOMO" if ship_horizontal else "PIONOWO"
                        turn_text = (
                            f"FAZA ROZSTAWIANIA: Ustaw {next_ship.name} "
                            f"({orient}) [R/SPACJA - obrót]"
                        )
                        turn_color = (100, 200, 255)
                    else:
                        turn_text = "ZATWIERDZANIE ROZSTAWIENIA..."
                        turn_color = (255, 255, 255)

                # Sytuacja 2: Ty skończyłeś, ale serwer wciąż utrzymuje
                # SHIP_PLACEMENT (przeciwnik rozstawia)
                elif ready_sent and gm.game_state == GameState.SHIP_PLACEMENT:
                    turn_text = (
                        "WSZYSTKIE STATKI POSTAWIONE! Oczekiwanie na "
                        "zakończenie rozstawiania przez przeciwnika..."
                    )
                    turn_color = (255, 165, 0)

                # Sytuacja 3: Bitwa!
                else:
                    if gm.network_client.is_my_turn:
                        turn_text = "TWOJA TURA (STRZELAJ NA RADARZE!)"
                        turn_color = (50, 255, 50)
                    else:
                        turn_text = "TURA PRZECIWNIKA"
                        turn_color = (255, 50, 50)
            else:
                turn_text = "OCZEKIWANIE NA POŁĄCZENIE..."
                turn_color = (255, 255, 0)

            turn_surface = info_font.render(turn_text, True, turn_color)
            screen.blit(turn_surface, (20, 560))

            if server and current_host_ip:
                ip_surface = info_font.render(
                    f"HOST IP: {current_host_ip}", True, (150, 150, 255)
                )
                screen.blit(ip_surface, (20, 530))

        pygame.display.flip()
        clock.tick(60)

    if gm and gm.network_client:
        gm.network_client.disconnect()
    if server:
        server.stop()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
