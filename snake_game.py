import pygame
import random
import sys

# --- Game Configuration ---
GAME_WIDTH = 500
GAME_HEIGHT = 500
SPACE_SIZE = 20
SPEED = 10  # frames per second

SNAKE_COLOR = (0, 255, 0)
FOOD_COLOR = (255, 0, 0)
BG_COLOR = (0, 0, 0)
SCORE_COLOR = (255, 255, 255)
GAMEOVER_COLOR = (255, 0, 0)

COLS = GAME_WIDTH // SPACE_SIZE
ROWS = GAME_HEIGHT // SPACE_SIZE


class Snake:
    def __init__(self):
        self.direction = "RIGHT"
        # Start with 3 segments moving right from the center
        start_x = COLS // 2
        start_y = ROWS // 2
        self.body = [
            [start_x - i, start_y] for i in range(3)
        ]

    def move(self):
        head_x, head_y = self.body[0]

        if self.direction == "UP":
            head_y -= 1
        elif self.direction == "DOWN":
            head_y += 1
        elif self.direction == "LEFT":
            head_x -= 1
        elif self.direction == "RIGHT":
            head_x += 1

        self.body.insert(0, [head_x, head_y])
        self.body.pop()  # remove tail (grows when food eaten before pop)

    def grow(self):
        # Duplicate the tail so next move keeps the extra segment
        self.body.append(self.body[-1][:])

    def change_direction(self, new_direction):
        opposites = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
        if new_direction != opposites.get(self.direction):
            self.direction = new_direction

    def check_wall_collision(self):
        head_x, head_y = self.body[0]
        return head_x < 0 or head_x >= COLS or head_y < 0 or head_y >= ROWS

    def check_self_collision(self):
        return self.body[0] in self.body[1:]


class Food:
    def __init__(self, snake_body):
        self.position = self._random_position(snake_body)

    def _random_position(self, snake_body):
        while True:
            pos = [random.randint(0, COLS - 1), random.randint(0, ROWS - 1)]
            if pos not in snake_body:
                return pos

    def respawn(self, snake_body):
        self.position = self._random_position(snake_body)


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT + 40))
        pygame.display.set_caption("Snake Game")
        self.clock = pygame.time.Clock()
        self.font_score = pygame.font.SysFont("consolas", 20)
        self.font_large = pygame.font.SysFont("consolas", 44, bold=True)
        self.font_medium = pygame.font.SysFont("consolas", 24)
        self.reset()

    def reset(self):
        self.snake = Snake()
        self.food = Food(self.snake.body)
        self.score = 0
        self.running = True

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.snake.change_direction("UP")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.snake.change_direction("DOWN")
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.snake.change_direction("LEFT")
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.snake.change_direction("RIGHT")

    def update(self):
        self.snake.move()

        # Check food collision
        if self.snake.body[0] == self.food.position:
            self.score += 1
            self.snake.grow()
            self.food.respawn(self.snake.body)

        # Check death conditions
        if self.snake.check_wall_collision() or self.snake.check_self_collision():
            self.running = False

    def draw(self):
        self.screen.fill(BG_COLOR)

        # Draw score bar
        score_surf = self.font_score.render(f"Score: {self.score}", True, SCORE_COLOR)
        self.screen.blit(score_surf, (10, 8))

        # Offset game area below score bar
        offset_y = 40

        # Draw food
        fx, fy = self.food.position
        pygame.draw.ellipse(
            self.screen,
            FOOD_COLOR,
            (fx * SPACE_SIZE, fy * SPACE_SIZE + offset_y, SPACE_SIZE, SPACE_SIZE)
        )

        # Draw snake
        for i, (x, y) in enumerate(self.snake.body):
            color = (0, 200, 0) if i == 0 else SNAKE_COLOR  # darker head
            pygame.draw.rect(
                self.screen,
                color,
                (x * SPACE_SIZE, y * SPACE_SIZE + offset_y, SPACE_SIZE - 1, SPACE_SIZE - 1)
            )

        pygame.display.flip()

    def draw_game_over(self):
        self.screen.fill(BG_COLOR)

        go_surf = self.font_large.render("GAME OVER", True, GAMEOVER_COLOR)
        score_surf = self.font_medium.render(f"Final Score: {self.score}", True, SCORE_COLOR)
        restart_surf = self.font_medium.render("Press R to restart or Q to quit", True, (180, 180, 180))

        cx = GAME_WIDTH // 2
        cy = (GAME_HEIGHT + 40) // 2

        self.screen.blit(go_surf, go_surf.get_rect(center=(cx, cy - 50)))
        self.screen.blit(score_surf, score_surf.get_rect(center=(cx, cy + 10)))
        self.screen.blit(restart_surf, restart_surf.get_rect(center=(cx, cy + 55)))

        pygame.display.flip()

    def run(self):
        while True:
            if self.running:
                self.handle_events()
                self.update()
                self.draw()
                self.clock.tick(SPEED)
            else:
                self.draw_game_over()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_r:
                            self.reset()
                        elif event.key == pygame.K_q:
                            pygame.quit()
                            sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
