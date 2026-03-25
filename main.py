# Complete Functional Game Code

import pygame
import sys

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 800, 600
FPS = 60

# Setup the screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('My Game')

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)  

# Game Variables
clock = pygame.time.Clock()

# Drawing methods

def draw_background():
    screen.fill(WHITE)  # Fill the screen with white


def draw_hud():
    font = pygame.font.SysFont('Arial', 24)
    text = font.render('Score: 0', True, BLACK)
    screen.blit(text, (10, 10))  # Draw the HUD in the top-left corner

# Main game loop

def main():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        draw_background()  # Render the background
        draw_hud()  # Render the HUD

        pygame.display.flip()  # Update the display
        clock.tick(FPS)  # Maintain the frame rate

# Run the game
if __name__ == '__main__':
    main()