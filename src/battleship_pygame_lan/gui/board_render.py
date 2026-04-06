from typing import Protocol, runtime_checkable

import pygame

from ..logic.enums import FieldState

WHITE = (255, 255, 255)
SHIP_COLOR = (100, 100, 100)
MISS_COLOR = (150, 150, 255)
HIT_COLOR = (255, 50, 50)


@runtime_checkable
class BoardLike(Protocol):
    row: int
    column: int

    def get_field_state(self, row: int, col: int) -> FieldState: ...


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

    def draw(self, board: BoardLike, ox: int, oy: int, title: str) -> None:
        title_surf = pygame.font.SysFont("Arial", 24, bold=True).render(
            title, True, WHITE
        )
        self.screen.blit(title_surf, (ox, oy - 40))

        for r in range(board.row):
            self.screen.blit(
                self.font.render(str(r), True, WHITE), (ox - 25, oy + r * 42 + 10)
            )
            for c in range(board.column):
                if r == 0:
                    self.screen.blit(
                        self.font.render(str(c), True, WHITE),
                        (ox + c * 42 + 15, oy - 20),
                    )

                rect = pygame.Rect(ox + c * 42, oy + r * 42, 40, 40)
                state = board.get_field_state(r, c)
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
                elif state == FieldState.Empty:
                    highlight = tuple(min(255, v + 30) for v in base_color)
                    pygame.draw.line(
                        self.screen,
                        highlight,
                        (rect.left + 2, rect.top + 2),
                        (rect.right - 2, rect.top + 2),
                        2,
                    )

                pygame.draw.rect(self.screen, (20, 40, 70), rect, 1)

    def get_clicked_cell(
        self, pos: tuple[int, int], ox: int, oy: int
    ) -> tuple[int, int] | None:
        col, row = (pos[0] - ox) // 42, (pos[1] - oy) // 42
        return (int(row), int(col)) if 0 <= row < 10 and 0 <= col < 10 else None
