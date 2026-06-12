import logging
import socket
import sys
import threading
from queue import Empty

import pygame

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
        return ip
    except Exception:
        return "127.0.0.1"


def get_next_needed_ship(gm: GameManager) -> ShipType | None:
    """Zwraca kolejny typ statku, który gracz musi jeszcze rozstawić."""
    order = [
        ShipType.FourMaster,
        ShipType.ThreeMaster,
        ShipType.TwoMaster,
        ShipType.OneMaster,
    ]
    for ship_type in order:
        if gm.player.available_ships[ship_type] > 0:
            return ship_type
    return None


def main() -> None:
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        filename="battleships.log",
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
        hit_sound = pygame.mixer.Sound("assets/sounds/hit.mp3")
        miss_sound = pygame.mixer.Sound("assets/sounds/miss.mp3")
        print("[AUDIO] Pomyślnie załadowano dźwięki .mp3")
    except Exception as e:
        hit_sound = None
        miss_sound = None
        print(f"[MUTE] Brak plików dźwiękowych: {e}")

    info_font = pygame.font.SysFont("Arial", 22, bold=True)

    menu = MainMenu(screen)
    renderer = BoardRenderer(screen)

    gm: GameManager | None = None
    server: NetworkServer | None = None
    current_host_ip = ""

    ready_sent = False
    valid_ready_type = ReadyType.SHIP_PLACED.value

    game_state = "MENU"
    running = True

    # Kierunek stawiania statku (True = poziomo, False = pionowo)
    ship_horizontal = True

    while running:
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

                    print(f"[GM] Inicjalizacja hosta pod IP: {current_host_ip}")
                    gm = GameManager(
                        player_name=menu.player_name, server_ip=current_host_ip
                    )
                    gm.connect()

                    ready_sent = False
                    game_state = "GAME"

                elif action == "join_final":
                    target_ip = getattr(menu, "target_ip", "127.0.0.1")
                    print(f"\n[KLIENT] Łączenie z hostem: {target_ip}...")

                    gm = GameManager(player_name=menu.player_name, server_ip=target_ip)
                    try:
                        gm.connect()
                        ready_sent = False
                        game_state = "GAME"
                    except Exception as e:
                        print(f"[BŁĄD] Połączenie nieudane: {e}")

                elif action == "quit":
                    running = False

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
                            f"[GRA] Orientacja statku: {'POZIOMA' if ship_horizontal else 'PIONOWA'}"
                        )

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = pygame.mouse.get_pos()

                    # 1. KLIKANIE W FAZIE ROZSTAWIANIA STATKÓW
                    if is_local_placement:
                        cell = renderer.get_clicked_cell(pos, 50, 80)
                        if cell:
                            row, col = cell
                            next_ship = get_next_needed_ship(gm)
                            if next_ship:
                                try:
                                    success = gm.player.place_ship(
                                        next_ship, row, col, ship_horizontal
                                    )
                                    if success:
                                        print(
                                            f"[GRA] Postawiono {next_ship.name} na pozycji {row, col}"
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
                                # Zapewniamy idealne dopasowanie wielkości liter imienia gracza z siecią,
                                # aby GameManager pomyślnie przetworzył pakiet trafienia/pudła.
                                gm.player.name = gm.network_client.player_name

                                # Przywrócone wywołanie z poprzedniego kroku
                                gm.shoot(row, col)
                            except Exception as e:
                                print(f"[GRA] Nie można oddać strzału: {e}")
                                logger.error(f"Błąd wysyłania ataku: {e}")

        # === OBSŁUGA SEKCJI SIECIOWEJ POPRZEZ MANAGER ===
        if gm and gm.network_client.connected:
            # Automatyczne wysłanie pakietu gotowości po rozstawieniu całej floty
            if (
                gm.network_client.enemy_name
                and gm.player.is_every_ship_placed
                and not ready_sent
            ):
                print(
                    f"[GRA] Flota gotowa. Wysyłanie pakietu SHIP_PLACED dla: {gm.player.name}"
                )
                ready_payload = build_ready_payload(
                    gm.player.name, valid_ready_type, True
                )
                gm.network_client.send_to_socket(
                    gm.network_client.client, ready_payload
                )
                ready_sent = True

            gm.handle_response()

            # --- KONSUMOWANIE KOLEJKI GUI + DŹWIĘKI ---
            try:
                while True:
                    gui_event = gm.gui_events_queue.get_nowait()
                    if gui_event == GuiEvent.ShotHit:
                        print("[GUI EVENT] Trafiony!")
                        if hit_sound:
                            hit_sound.play()
                    elif gui_event == GuiEvent.ShotMissed:
                        print("[GUI EVENT] Pudło!")
                        if miss_sound:
                            miss_sound.play()
                    elif gui_event == GuiEvent.GameLost:
                        print("[GUI EVENT] Przegrana...")
                        game_state = "MENU"
                    elif gui_event == GuiEvent.GameWon:
                        print("[GUI EVENT] Wygrana!")
                        game_state = "MENU"
                    gm.gui_events_queue.task_done()
            except Empty:
                pass

        # === RENDEROWANIE INTERFEJSU GRY ===
        if game_state == "MENU":
            menu.draw()
            ready_sent = False
        elif game_state == "GAME" and gm is not None:
            screen.fill((10, 10, 25))

            # Lewy ekran: Nasza flota
            renderer.draw(gm.player.board, 50, 80, f"FLEET: {gm.player.name}")
            # Prawy ekran: Radar przeciwnika
            renderer.draw(
                gm.player.radar,
                550,
                80,
                f"RADAR (OPPONENT: {gm.network_client.enemy_name or 'Oczekiwanie...'})",
            )

            is_local_placement = (
                gm.network_client.enemy_name is not None
                and not gm.player.is_every_ship_placed
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
                        turn_text = f"FAZA ROZSTAWIANIA: Ustaw {next_ship.name} ({orient}) [R/SPACJA - obrót]"
                        turn_color = (100, 200, 255)
                    else:
                        turn_text = "ZATWIERDZANIE ROZSTAWIENIA..."
                        turn_color = (255, 255, 255)

                # Sytuacja 2: Ty skończyłeś, ale serwer wciąż utrzymuje SHIP_PLACEMENT (przeciwnik rozstawia)
                elif ready_sent and gm.game_state == GameState.SHIP_PLACEMENT:
                    turn_text = "WSZYSTKIE STATKI POSTAWIONE! Oczekiwanie na zakończenie rozstawiania przez przeciwnika..."
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
