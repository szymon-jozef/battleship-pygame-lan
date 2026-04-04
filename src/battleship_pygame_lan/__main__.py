import logging
import sys

import pygame

from battleship_pygame_lan.gui import BoardRenderer, MainMenu
from battleship_pygame_lan.logic import Player


def main() -> None:
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        filename="battleships.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    pygame.init()
    screen = pygame.display.set_mode((1000, 600))
    pygame.display.set_caption("Battleships LAN")
    clock = pygame.time.Clock()

    menu = MainMenu(screen)
    renderer = BoardRenderer(screen)
    player1 = Player(menu.player_name)

    game_state = "MENU"
    running = True

    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

            if game_state == "MENU":
                action = menu.handle_events(event)

                if action == "settings_updated":
                    player1.name = menu.player_name

                elif action == "host":
                    game_state = "GAME"
                    logger.info(f"Server started as {player1.name}")

                elif action == "join_final":
                    game_state = "GAME"
                    target_ip = menu.host_ip
                    logger.info(f"Connecting with {target_ip} as {player1.name}")

                elif action == "quit":
                    running = False

            elif game_state == "GAME":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    game_state = "MENU"

        if game_state == "MENU":
            menu.draw()
        elif game_state == "GAME":
            screen.fill((10, 10, 25))
            renderer.draw(player1.board, 50, 80, f"FLEET: {player1.name}")
            renderer.draw(player1.radar, 550, 80, f"RADAR (HOST: {menu.host_ip})")

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
