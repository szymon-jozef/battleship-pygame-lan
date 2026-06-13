from typing import Protocol, runtime_checkable

import pygame

from ..logic.enums import FieldState

WHITE = (255, 255, 255)
SHIP_COLOR = (100, 100, 100)
MISS_COLOR = (150, 150, 255)
HIT_COLOR = (255, 50, 50)
HOVER_COLOR = (0, 220, 0)  # Zielony kolor dla podglądu rozstawianego statku

CELL_SIZE = 40
CELL_MARGIN = 2
GRID_STEP = CELL_SIZE + CELL_MARGIN
LABEL_OFFSET_X = 25
LABEL_OFFSET_Y = 10
COLUMN_LABEL_Y = 20
TITLE_OFFSET_Y = 40


@runtime_checkable
class BoardLike(Protocol):
    """
    Protocol defining the required interface for board-like objects.

    Any object used by the BoardRenderer must implement these attributes
    and methods to ensure compatibility between the logic and GUI layers.
    """

    row: int
    column: int

    def get_field_state(self, row: int, col: int) -> FieldState:
        """Return the FieldState at the given coordinates."""


class BoardRenderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 18)
        self.colors = {
            FieldState.Empty: (30, 60, 100),
            FieldState.Taken: SHIP_COLOR,
            FieldState.Missed: (40, 80, 140),
            FieldState.Hit: (60, 20, 20),
        }

    def draw(
        self,
        board: BoardLike,
        ox: int,
        oy: int,
        title: str,
        hover_cell: tuple[int, int] | None = None,
        hover_ship_info: tuple[int, bool] | None = None,
    ) -> None:
        title_surf = pygame.font.SysFont("Arial", 24, bold=True).render(
            title, True, WHITE
        )
        self.screen.blit(title_surf, (ox, oy - TITLE_OFFSET_Y))

        # Wyznaczanie kafelków zajmowanych przez podglądany statek
        preview_cells = set()
        if hover_cell and hover_ship_info:
            h_row, h_col = hover_cell
            ship_length, horizontal = hover_ship_info

            for i in range(ship_length):
                # Zmiana: dla pionu odejmujemy i (h_row - i), aby podgląd szedł w górę planszy
                r = h_row if horizontal else h_row - i
                c = h_col + i if horizontal else h_col

                # Dodajemy tylko te kafelki, które mieszczą się na planszy
                if 0 <= r < board.row and 0 <= c < board.column:
                    preview_cells.add((r, c))

        for r in range(board.row):
            label_y = oy + (r * GRID_STEP) + LABEL_OFFSET_Y
            self.screen.blit(
                self.font.render(str(r), True, WHITE), (ox - LABEL_OFFSET_X, label_y)
            )
            for c in range(board.column):
                if r == 0:
                    self.screen.blit(
                        self.font.render(str(c), True, WHITE),
                        (ox + (c * GRID_STEP) + 15, oy - COLUMN_LABEL_Y),
                    )

                rect = pygame.Rect(
                    ox + (c * GRID_STEP), oy + (r * GRID_STEP), CELL_SIZE, CELL_SIZE
                )
                state = board.get_field_state(r, c)

                # Jeżeli ten kafelek jest podświetlony przez podgląd, zmieniamy jego kolor
                if (r, c) in preview_cells:
                    base_color = HOVER_COLOR
                else:
                    base_color = self.colors.get(state, (30, 30, 60))

                pygame.draw.rect(self.screen, base_color, rect)

                if state == FieldState.Missed:
                    pygame.draw.circle(self.screen, MISS_COLOR, rect.center, 12, 2)
                    pygame.draw.circle(self.screen, MISS_COLOR, rect.center, 6, 1)
                elif state == FieldState.Hit:
                    pygame.draw.line(
                        self.screen,
                        HIT_COLOR,
                        (rect.left + 5, rect.top + 5),
                        (rect.right - 5, rect.bottom - 5),
                        3,
                    )
                    pygame.draw.line(
                        self.screen,
                        HIT_COLOR,
                        (rect.right - 5, rect.top + 5),
                        (rect.left + 5, rect.bottom - 5),
                        3,
                    )
                elif state == FieldState.Empty and (r, c) not in preview_cells:
                    highlight = tuple(min(255, v + 30) for v in base_color)
                    pygame.draw.line(
                        self.screen,
                        highlight,
                        (rect.left + 2, rect.top + 2),
                        (rect.right - 2, rect.top + 2),
                        2,
                    )

                # Rysowanie krawędzi kafelka (wyraźniejsza biała ramka dla podglądu)
                if (r, c) in preview_cells:
                    pygame.draw.rect(self.screen, (255, 255, 255), rect, 1)
                else:
                    pygame.draw.rect(self.screen, (20, 40, 70), rect, 1)

    def get_clicked_cell(
        self, pos: tuple[int, int], ox: int, oy: int
    ) -> tuple[int, int] | None:
        col, row = (pos[0] - ox) // GRID_STEP, (pos[1] - oy) // GRID_STEP
        return (int(row), int(col)) if 0 <= row < 10 and 0 <= col < 10 else None
