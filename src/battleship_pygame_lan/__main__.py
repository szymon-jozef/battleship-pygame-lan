import argparse
import contextlib
import logging
import socket
import sys
import threading
import time
from importlib.metadata import version
from pathlib import Path
from queue import Empty

import pygame
from appdirs import user_log_dir  # type: ignore

from battleship_pygame_lan.game_manager import GameManager
from battleship_pygame_lan.game_manager.enums import GuiEvent
from battleship_pygame_lan.gui.board_render import BoardRenderer
from battleship_pygame_lan.gui.main_menu import MainMenu, get_assets_path
from battleship_pygame_lan.logic import ShipType
from battleship_pygame_lan.logic.enums import FieldState
from battleship_pygame_lan.network import GameState
from battleship_pygame_lan.network.models import ReadyType
from battleship_pygame_lan.network.server import NetworkServer


def get_local_ip() -> str:
    """Gets your local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return str(ip)
    except Exception:
        return "127.0.0.1"


def get_next_needed_ship(gm: GameManager) -> ShipType | None:
    """Returns next shipe type, which player must place."""
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
    """Renders player stats on game end."""
    screen.fill((15, 15, 35))

    title_text = f"{winner_name.upper()} WINS!"
    title_surf = font_title.render(title_text, True, (255, 215, 0))
    title_rect = title_surf.get_rect(center=(500, 80))
    screen.blit(title_surf, title_rect)

    total_shots = stats["shots"]
    accuracy = (stats["hits"] / total_shots * 100) if total_shots > 0 else 0.0

    stats_labels = [
        f"Shots fired: {stats['shots']}",
        f"Hits: {stats['hits']}",
        f"Misses: {stats['misses']}",
        f"Accuracy: {accuracy:.1f}%",
        f"Ships destroyed: {stats['sunk']}/10",
        f"Consecutive hits: {stats['max_streak']}",
    ]

    start_y = 160
    for i, label in enumerate(stats_labels):
        surf = font_stats.render(label, True, (220, 220, 255))
        rect = surf.get_rect(center=(500, start_y + i * 40))
        screen.blit(surf, rect)

    # Return to menu button
    btn_rect = pygame.Rect(400, 480, 200, 50)
    pygame.draw.rect(screen, (40, 80, 150), btn_rect, border_radius=8)
    pygame.draw.rect(screen, (255, 255, 255), btn_rect, 2, border_radius=8)

    btn_text = font_stats.render("Return to MENU", True, (255, 255, 255))
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
    if pygame.mixer:
        with contextlib.suppress(pygame.error):
            pygame.mixer.init()

    if pygame.mixer and not pygame.mixer.get_init():
        logger.warning("[Main] No sound device detected. No sound will be played!")
        pygame.mixer = None

    screen = pygame.display.set_mode((1000, 600))
    pygame.display.set_caption("Battleship LAN")
    clock = pygame.time.Clock()

    assets_path: Path = Path(get_assets_path())

    hit_sound_path = assets_path.joinpath("sfx/hit.ogg")
    miss_sound_path = assets_path.joinpath("sfx/miss.ogg")
    sink_sound_path = assets_path.joinpath("sfx/sink.ogg")

    hit_sound = None
    miss_sound = None
    sink_sound = None

    if pygame.mixer:
        hit_sound = pygame.mixer.Sound(hit_sound_path)
        miss_sound = pygame.mixer.Sound(miss_sound_path)
        sink_sound = pygame.mixer.Sound(sink_sound_path)

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

    # Player Stats
    player_stats = {
        "shots": 0,
        "hits": 0,
        "misses": 0,
        "sunk": 0,
        "current_streak": 0,
        "max_streak": 0,
    }
    end_game_winner = ""

    # Ship placement directions
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
                    print(f"\n[KLIENT] Connecting to host: {target_ip}...")

                    gm = GameManager(player_name=menu.player_name, server_ip=target_ip)
                    try:
                        gm.connect()
                        ready_sent = False
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
                        print(f"[ERROR] Connection failed: {e}")

                elif action == "quit":
                    running = False

            elif game_state == "END_SCREEN":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    btn_rect = draw_end_screen(
                        screen,
                        end_title_font,
                        end_stats_font,
                        end_game_winner,
                        player_stats,
                    )
                    if btn_rect.collidepoint(event.pos):
                        if server:
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
                            f"[GAME] Ship orientation: "
                            f"{'HORIZONTAL' if ship_horizontal else 'VERTICAL'}"
                        )

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Placing ships
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
                                            "[Game] Ship "
                                            f"{next_ship.name} placed on {row, col}"
                                        )
                                except Exception as e:
                                    print(f"[Game] Can't place ship: {e}")
                                    logger.error(f"Ship placement failed: {e}")

                    # Shooting ships
                    elif (
                        gm.network_client.enemy_name
                        and gm.player.is_every_ship_placed
                        and gm.game_state != GameState.SHIP_PLACEMENT
                        and gm.network_client.is_my_turn
                    ):
                        cell = renderer.get_clicked_cell(pos, 550, 80)
                        if cell:
                            row, col = cell
                            current_state = gm.player.radar.get_field_state(row, col)

                        if current_state in (FieldState.Empty, FieldState.Taken):
                            try:
                                gm.player.name = gm.network_client.player_name
                                gm.shoot(row, col)
                            except Exception as e:
                                print(f"[Game] Can't shot: {e}")
                                logger.error(f"Cannot send attack: {e}")

        # Game manager
        if game_state == "GAME" and gm and gm.network_client.connected:
            if (
                gm.network_client.enemy_name
                and gm.player.is_every_ship_placed
                and not ready_sent
            ):
                print(f"[Game] Fleet ready. Sending SHIP_PLACED to: {gm.player.name}")
                gm.network_client.ready(valid_ready_type)
                ready_sent = True

            gm.handle_response()

            # GUI, SOUND, etc.
            try:
                while True:
                    gui_event = gm.gui_events_queue.get_nowait()

                    match gui_event:
                        case GuiEvent.ShotHit:
                            print("[GUI EVENT] HIT!")
                            if hit_sound:
                                hit_sound.play()

                            player_stats["shots"] += 1
                            player_stats["hits"] += 1
                            player_stats["current_streak"] += 1

                            if (
                                player_stats["current_streak"]
                                > player_stats["max_streak"]
                            ):
                                player_stats["max_streak"] = player_stats[
                                    "current_streak"
                                ]

                        case GuiEvent.ShotSunk:
                            print("[GUI EVENT] SHIP SUNK!")
                            if sink_sound:
                                sink_sound.play()

                            player_stats["shots"] += 1
                            player_stats["hits"] += 1
                            player_stats["sunk"] += 1
                            player_stats["current_streak"] += 1

                        case GuiEvent.ShotMissed:
                            print("[GUI EVENT] MISS!")
                            if miss_sound:
                                miss_sound.play()

                            player_stats["shots"] += 1
                            player_stats["misses"] += 1
                            player_stats["current_streak"] = 0

                        case GuiEvent.GameLost:
                            print("[GUI EVENT] You lost...")
                            end_game_winner = (
                                gm.network_client.enemy_name or "UNKNOWN ENEMY"
                            )
                            game_state = "END_SCREEN"

                        case GuiEvent.GameWon:
                            print("[GUI EVENT] You won!")
                            end_game_winner = menu.player_name
                            game_state = "END_SCREEN"

                    gm.gui_events_queue.task_done()
            except Empty:
                pass

        # Rendering game interface
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

            # Ship preview
            hover_cell = None
            hover_ship_info = None

            if is_local_placement:
                hover_cell = renderer.get_clicked_cell(pos, 50, 80)
                if hover_cell:
                    next_ship = get_next_needed_ship(gm)
                    if next_ship:
                        hover_ship_info = (next_ship.value, ship_horizontal)

            # Left Board
            renderer.draw(
                gm.player.board,
                50,
                80,
                f"{gm.player.name}",
                hover_cell=hover_cell,
                hover_ship_info=hover_ship_info,
            )

            # Righ Board
            renderer.draw(
                gm.player.radar,
                550,
                80,
                f"{gm.network_client.enemy_name or 'Waiting for player...'}",
            )

            # Bottom Board
            if gm.network_client.connected:
                if not gm.network_client.enemy_name:
                    turn_text = "Waiting for player..."
                    turn_color = (255, 255, 0)

                # Placing ships
                elif is_local_placement:
                    next_ship = get_next_needed_ship(gm)
                    if next_ship:
                        orient = "HORIZONTAL" if ship_horizontal else "VERTICAL"
                        turn_text = (
                            f"Place Ship: {next_ship.name} "
                            f"({orient}) [R/SPACE - rotate]"
                        )
                        turn_color = (100, 200, 255)

                # Battle
                else:
                    if gm.network_client.is_my_turn:
                        turn_text = "Your Turn (Click any point on the radar to shot)"
                        turn_color = (50, 255, 50)
                    else:
                        turn_text = "Waiting for your turn"
                        turn_color = (255, 50, 50)
            else:
                turn_text = "Connection lost..."
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

    sys.exit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Battleship-pygame-lan")
    parser.add_argument(
        "--version", action="store_true", help="Display version and exit"
    )
    parsed = parser.parse_args()

    if parsed.version:
        print("Version: ", version("battleship_pygame_lan"))
    else:
        main()
