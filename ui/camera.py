import math
import pygame


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
        accel = 5000  # Accélération (pixels/s^2)
        friction_coeff = 0.01

        move_x = 0
        move_y = 0
        if keys[pygame.K_z]:
            move_y -= 1
        if keys[pygame.K_s]:
            move_y += 1
        if keys[pygame.K_q]:
            move_x -= 1
        if keys[pygame.K_d]:
            move_x += 1

        if move_x != 0 or move_y != 0:
            inv = 1 / math.sqrt(2)
            move_x *= inv
            move_y *= inv

            self.dx += move_x * accel * dt
            self.dy += move_y * accel * dt

        self.dx *= math.pow(friction_coeff, dt)
        self.dy *= math.pow(friction_coeff, dt)

        if abs(self.dx) < 1:
            self.dx = 0
        if abs(self.dy) < 1:
            self.dy = 0

        self.x += (self.dx / self.zoom) * dt
        self.y += (self.dy / self.zoom) * dt

        # clamp caméra
        max_x = game_map.width * tile_size - window_w / self.zoom
        max_y = game_map.height * tile_size - window_h / self.zoom

        self.x = max(0, min(self.x, max_x))
        self.y = max(0, min(self.y, max_y))

    def apply_zoom(self, mouse_pos, zoom_delta):
        mx, my = mouse_pos

        before = screen_to_world(mx, my, self.x, self.y, self.zoom)

        self.zoom *= 1 + zoom_delta * 0.1
        self.zoom = max(1, min(self.zoom, 25))

        after = screen_to_world(mx, my, self.x, self.y, self.zoom)

        self.x += before[0] - after[0]
        self.y += before[1] - after[1]
