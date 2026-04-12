import pygame

from config import GameConfig as gc
from ui.camera import screen_to_world



def lighten(color, amount=40):
    return tuple(min(255, c + amount) for c in color)


def compute_tile_size(window_w, window_h):
    return min(window_w // gc.WIDTH, window_h // gc.HEIGHT)


def draw_centers(screen, game_map, tile_size, cam):
    for tile in game_map.tiles.values():
        x, y = tile.center
        wx = x * tile_size
        wy = y * tile_size
        sx, sy = world_to_screen(wx, wy, cam.x, cam.y, cam.zoom)

        pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 3)

        text = font.render(f"{tile.area}:{tile.id}", True, (255, 255, 255))
        screen.blit(text, (sx - 10, sy - 15))


def get_hovered_tile(game_map, cam, tile_size):
    mouse_x, mouse_y = pygame.mouse.get_pos()

    world_x, world_y = screen_to_world(mouse_x, mouse_y, cam.x, cam.y, cam.zoom)

    grid_x = int(world_x // tile_size)
    grid_y = int(world_y // tile_size)

    if 0 <= grid_x < game_map.width and 0 <= grid_y < game_map.height:
        tile_id = game_map.grid[grid_y][grid_x]
        return game_map.tiles.get(tile_id)

    return None
