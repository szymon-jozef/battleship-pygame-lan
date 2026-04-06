import logging
import os
import sys

import pygame

from battleship_pygame_lan.gui import BoardRenderer, MainMenu
from battleship_pygame_lan.logic import Player
from battleship_pygame_lan.logic.enums import ShipType


def main() -> None:
    # --- Logging Setup ---
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        filename="battleships.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # --- Pygame Initialization ---
    pygame.init()
    pygame.mixer.init()

    screen = pygame.display.set_mode((1000, 600))
    pygame.display.set_caption("Battleship LAN")
    clock = pygame.time.Clock()

    menu = MainMenu(screen)
    renderer = BoardRenderer(screen)

    # --- Game Logic Initialization ---
    player1 = Player(menu.player_name)
    enemy = Player("Bot #1")

    try:
        # Example ship placements
        player1.place_ship(ShipType.ThreeMaster, 1, 1)
        player1.place_ship(ShipType.FourMaster, 5, 5, False)

        enemy.place_ship(ShipType.FourMaster, 2, 2)
        enemy.place_ship(ShipType.TwoMaster, 7, 1, False)
    except Exception as e:
        logger.error(f"Initial ship placement failed: {e}")

    game_state = "MENU"
    running = True

    # --- Main Game Loop ---
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

            if game_state == "MENU":
                action = menu.handle_events(event)
                if action == "settings_updated":
                    player1.name = menu.player_name
                elif action in ["host", "join_final"]:
                    game_state = "GAME"
                elif action == "quit":
                    running = False

            elif game_state == "GAME":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    game_state = "MENU"

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = pygame.mouse.get_pos()
                    cell = renderer.get_clicked_cell(pos, 550, 80)
                    if cell:
                        row, col = cell
                        result = enemy.receive_shot(row, col)
                        player1.mark_shot(row, col, result)

                        # --- NEW: Play combat sound effect ---
                        menu.play_combat_sound(result)

        # --- Rendering ---
        if game_state == "MENU":
            menu.draw()
        elif game_state == "GAME":
            screen.fill((10, 10, 25))
            renderer.draw(player1.board, 50, 80, f"FLEET: {player1.name}")
            renderer.draw(player1.radar, 550, 80, f"RADAR (OPPONENT: {enemy.name})")

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
