import math
import pygame  # type: ignore


def speed_coeff(zoom):
    return max(1, 1 / (math.atan((zoom - 1.2) * math.pi) / math.pi + 0.4))


def world_to_screen(x, y, camera_x, camera_y, zoom):
    return int((x - camera_x) * zoom), int((y - camera_y) * zoom)


def screen_to_world(x, y, camera_x, camera_y, zoom):
    return (x / zoom + camera_x), (y / zoom + camera_y)


class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.zoom = 1.0

        self.dx = 0
        self.dy = 0

    def update(self, dt, game_map, tile_size, window_w, window_h):
        keys = pygame.key.get_pressed()
        move_speed = 10

        self.dx /= 1.65 + 20 * dt
        self.dy /= 1.65 + 20 * dt

        if keys[pygame.K_z]:
            self.dy -= move_speed * dt / self.zoom
        if keys[pygame.K_s]:
            self.dy += move_speed * dt / self.zoom
        if keys[pygame.K_q]:
            self.dx -= move_speed * dt / self.zoom
        if keys[pygame.K_d]:
            self.dx += move_speed * dt / self.zoom

        if abs(self.dx) > 0.05 or abs(self.dy) > 0.05:
            norm = (self.dx**2 + self.dy**2) ** 0.5
            self.x += self.dx / norm * speed_coeff(self.zoom) * move_speed
            self.y += self.dy / norm * speed_coeff(self.zoom) * move_speed

        # clamp caméra
        self.x = min(game_map.width * tile_size - window_w / self.zoom, max(0, self.x))
        self.y = min(game_map.height * tile_size - window_h / self.zoom, max(0, self.y))

    def apply_zoom(self, mouse_pos, zoom_delta):
        mx, my = mouse_pos

        before = screen_to_world(mx, my, self.x, self.y, self.zoom)

        self.zoom *= 1 + zoom_delta * 0.1
        self.zoom = max(1, min(self.zoom, 5))

        after = screen_to_world(mx, my, self.x, self.y, self.zoom)

        self.x += before[0] - after[0]
        self.y += before[1] - after[1]
