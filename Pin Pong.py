import pygame
from pygame.locals import *
import random
import math

pygame.init()
pygame.mixer.init()

# -------------------- ПАРАМЕТРЫ --------------------
screen_width = 600
screen_height = 500
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption('Pong Evolution')
icon = pygame.image.load('welllwelllwelll8.jpg')
pygame.display.set_icon(icon)

# Цвета
background = (50, 25, 50)
white = (255, 255, 255)
black = (0, 0, 0)
gray = (180, 180, 180)
red = (255, 50, 50)
yellow = (255, 255, 0)
green = (0, 255, 0)

# Шрифты
font = pygame.font.Font('Squealer.otf', 36)
font_big = pygame.font.Font('Squealer.otf', 72)
menu_font = pygame.font.Font('Squealer.otf', 42)

# Пульсация меню
menu_timer = 0
menu_pulse_amplitude = 10
menu_swing_angle = 5

# Музыка
music_menu = 'Sun Araw - Horse Steppin _ Hotline Miami OST.mp3'
music_easy = 'Hotline Miami Soundtrack ~ Crystals [QXkSYSPTpj4].mp3'
music_medium = 'Perturbator - Miami Disco _ Hotline Miami OST.mp3'
music_hard = 'Jasper Byrne - Hotline _ Hotline Miami OST.mp3'
music_pvp = 'Perturbator - Vengance _ Hotline Miami OST.mp3'
goal_sound = pygame.mixer.Sound('Windows Error Sound effect.mp3')
lose_sound = pygame.mixer.Sound('GOAL.mp3')

# -------------------- ФУНКЦИИ --------------------
def play_music(track):
    pygame.mixer.music.load(track)
    pygame.mixer.music.play(-1)
    pygame.mixer.music.set_volume(0.2)

def draw_text(text, font, color, x, y, center=False):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    screen.blit(img, rect)

def draw_board():
    screen.fill(background)
    pygame.draw.line(screen, white, (0, 50), (screen_width, 50))

# -------------------- КЛАССЫ --------------------
class Button:
    def __init__(self, x, y, w, h, text):
        self.rect = Rect(x, y, w, h)
        self.text = text
        self.hovered_last = False

    def draw(self):
        mouse_pos = pygame.mouse.get_pos()
        hovered = self.rect.collidepoint(mouse_pos)
        color = gray if hovered else white
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        text_img = menu_font.render(self.text, True, black)
        text_rect = text_img.get_rect(center=self.rect.center)
        screen.blit(text_img, text_rect)
        # Проигрываем звук один раз при наведении
        if hovered and not self.hovered_last:
            pygame.mixer.Sound('zvuk-perezariadki-ak47.mp3').play().set_volume(0.5)
        self.hovered_last = hovered

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class Paddle:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 20, 100)
        self.speed = 5
        self.reaction_time = 0

    def move(self, up_key, down_key):
        keys = pygame.key.get_pressed()
        if keys[up_key] and self.rect.top > 50:
            self.rect.move_ip(0, -self.speed)
        if keys[down_key] and self.rect.bottom < screen_height:
            self.rect.move_ip(0, self.speed)

    def ai(self, ball, difficulty):
        if self.reaction_time > 0:
            self.reaction_time -= 1
            return
        if difficulty == "easy":
            speed_factor = 0.5
        elif difficulty == "medium":
            speed_factor = 1
        else:
            speed_factor = 2
        if self.rect.centery < ball.rect.top and self.rect.bottom < screen_height:
            self.rect.move_ip(0, int(self.speed * speed_factor))
        elif self.rect.centery > ball.rect.bottom and self.rect.top > 50:
            self.rect.move_ip(0, -int(self.speed * speed_factor))

    def draw(self):
        pygame.draw.rect(screen, white, self.rect)

# -------------------- КЛАССЫ --------------------
class Ball:
    def __init__(self, x, y, speed):
        self.rect = pygame.Rect(x, y, 16, 16)
        self.initial_speed_x = speed
        self.initial_speed_y = speed
        self.speed_x = random.choice([-speed, speed])
        self.speed_y = random.choice([-speed, speed])
        self.radius = 8
        self.effect_end_time = None  # таймер для восстановления скорости после стены
        self.last_hit = None  # "player" или "cpu"

    def move(self, paddles, boosters, walls):
        # Восстановление стандартной скорости, если эффект закончился
        if self.effect_end_time and pygame.time.get_ticks() >= self.effect_end_time:
            self.speed_x = self.initial_speed_x * (1 if self.speed_x > 0 else -1)
            self.speed_y = self.initial_speed_y * (1 if self.speed_y > 0 else -1)
            self.effect_end_time = None

        # Отскок от верхней и нижней границы
        if self.rect.top < 50 or self.rect.bottom > screen_height:
            self.speed_y *= -1

        # Отскок от ракеток
        for p, name in paddles:  # Передаём список кортежей: (ракета, "player"/"cpu")
            if self.rect.colliderect(p.rect):
                self.speed_x *= -1
                self.last_hit = name

        # Взаимодействие с бустерами
        for b in boosters[:]:
            if self.rect.colliderect(b.rect) and not b.used:
                b.activate(self, self.last_hit)
                boosters.remove(b)
                pygame.time.set_timer(pygame.USEREVENT + 1, 2000)

        # Взаимодействие со стенами
        for w in walls:
            if w.visible and self.rect.colliderect(w.rect) and not getattr(w, 'used', False):
                w.used = True
                if w.type == "solid":
                    self.speed_x *= -1
                elif w.type == "slow":
                    self.speed_x *= 0.6
                    self.speed_y *= 0.6
                    self.effect_end_time = pygame.time.get_ticks() + 4000
                elif w.type == "fast":
                    self.speed_x *= 1.2
                    self.speed_y *= 1.2
                    self.effect_end_time = pygame.time.get_ticks() + 4000

        # Движение мяча
        self.rect.x += self.speed_x
        self.rect.y += self.speed_y

        # Проверка гола
        if self.rect.left < 0:
            return 1  # AI забил
        elif self.rect.right > screen_width:
            return -1  # игрок забил
        return 0

    def draw(self):
        pygame.draw.circle(screen, white, self.rect.center, self.radius)


class Wall:
    def __init__(self, x, y, w, h, wall_type="solid"):
        self.rect = pygame.Rect(x, y, w, h)
        self.type = wall_type
        self.visible = True
        self.spawn_time = pygame.time.get_ticks()
        self.duration = 4000  # 4 секунды
        self.used = False  # чтобы срабатывала только один раз

    def draw(self):
        color = red if self.type=="solid" else yellow if self.type=="slow" else green
        if self.type in ["slow","fast"]:
            s = pygame.Surface((self.rect.width,self.rect.height),pygame.SRCALPHA)
            s.fill((*color,128))
            screen.blit(s,self.rect.topleft)
        else:
            pygame.draw.rect(screen,color,self.rect)

    def update(self):
        if pygame.time.get_ticks() - self.spawn_time >= self.duration:
            self.visible=False


class Booster:
    def __init__(self):
        self.rect = Rect(random.randint(50, screen_width - 70), 50, 20, 20)
        self.effect = random.choice(["speed_up", "slow", "big_paddle"])
        self.color = (0, 255, 0) if self.effect=="speed_up" else (255, 255, 0) if self.effect=="slow" else (0, 150, 255)
        self.used = False  # срабатывает только один раз

    def move(self):
        self.rect.move_ip(0, 2)

    def draw(self):
        pygame.draw.rect(screen, self.color, self.rect)

    def activate(self, ball, last_hit):
        if self.used:
            return
        self.used = True
        if self.effect=="speed_up":
            ball.speed_x *= 1.5
            ball.speed_y *= 1.5
        elif self.effect=="slow":
            ball.speed_x *= 0.7
            ball.speed_y *= 0.7
        elif self.effect=="big_paddle":
            if last_hit == "player":
                player_paddle.rect.height += 25
            else:
                cpu_paddle.rect.height += 25
# -------------------- ОСНОВНОЙ ЦИКЛ --------------------
state = "menu"
difficulty = None
player_score = cpu_score = 0
fpsClock = pygame.time.Clock()
fps = 60
waiting_for_key = False  # Флаг ожидания нажатия клавиши после гола

btn_ai = Button(200, 200, 200, 50, "AI MODE")
btn_pvp = Button(200, 270, 200, 50, "PvsP")
btn_exit = Button(200, 340, 200, 50, "Exit")

btn_easy = Button(200, 200, 200, 50, "Easy")
btn_med = Button(200, 270, 200, 50, "Medium")
btn_hard = Button(200, 340, 200, 50, "Hard")

player_paddle = Paddle(20, screen_height // 2)
cpu_paddle = Paddle(screen_width - 40, screen_height // 2)
pong = Ball(screen_width // 2, screen_height // 2, 4)
boosters = []
walls = []
wall_timer = booster_timer = 0
game_timer = 0
mode = "ai"

play_music(music_menu)

running = True
while running:
    fpsClock.tick(fps)
    screen.fill(background)

    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        if event.type == MOUSEBUTTONDOWN:
            pos = event.pos
            if state == "menu":
                if btn_ai.is_clicked(pos):
                    state = "difficulty"
                    pygame.mixer.Sound('odinochn-vystrel-aks.mp3').play().set_volume(0.5)
                elif btn_pvp.is_clicked(pos):
                    mode = "pvp"
                    state = "game"
                    play_music(music_pvp)
                    pygame.mixer.Sound('odinochn-vystrel-aks.mp3').play().set_volume(0.5)
                elif btn_exit.is_clicked(pos):
                    running = False
            elif state == "difficulty":
                if btn_easy.is_clicked(pos):
                    difficulty = "easy"
                    play_music(music_easy)
                    state = "game"
                    pygame.mixer.Sound('odinochn-vystrel-aks.mp3').play().set_volume(0.5)
                elif btn_med.is_clicked(pos):
                    difficulty = "medium"
                    play_music(music_medium)
                    state = "game"
                    pygame.mixer.Sound('odinochn-vystrel-aks.mp3').play().set_volume(0.5)
                elif btn_hard.is_clicked(pos):
                    difficulty = "hard"
                    play_music(music_hard)
                    state = "game"
                    pygame.mixer.Sound('odinochn-vystrel-aks.mp3').play().set_volume(0.5)

        # Если ждём нажатие клавиши после гола
        if waiting_for_key:
            if event.type == KEYDOWN:
                waiting_for_key = False

    # -------------------- МЕНЮ --------------------
    if state == "menu":
        menu_timer += 1
        pulse_offset = math.sin(menu_timer * 0.05) * menu_pulse_amplitude
        swing_angle = math.sin(menu_timer * 0.05) * menu_swing_angle
        text_img = font_big.render("PONG", True, white)
        text_rect = text_img.get_rect(center=(300, 120 + pulse_offset))
        rotated_img = pygame.transform.rotate(text_img, swing_angle)
        rotated_rect = rotated_img.get_rect(center=text_rect.center)
        screen.blit(rotated_img, rotated_rect)
        btn_ai.draw()
        btn_pvp.draw()
        btn_exit.draw()

    # -------------------- ВЫБОР СЛОЖНОСТИ --------------------
    elif state == "difficulty":
        menu_timer += 1
        pulse_offset = math.sin(menu_timer * 0.05) * menu_pulse_amplitude
        swing_angle = math.sin(menu_timer * 0.05) * menu_swing_angle
        text_img = font_big.render("Choose Your Way", True, white)
        text_rect = text_img.get_rect(center=(300, 120 + pulse_offset))
        rotated_img = pygame.transform.rotate(text_img, swing_angle)
        rotated_rect = rotated_img.get_rect(center=text_rect.center)
        screen.blit(rotated_img, rotated_rect)
        btn_easy.draw()
        btn_med.draw()
        btn_hard.draw()

    # -------------------- ИГРА --------------------
    elif state == "game":
        draw_board()
        if mode == "pvp":
            draw_text(f"P1: {player_score}   P2: {cpu_score}", font, white, 200, 10)
        else:  # против ИИ
            draw_text(f"P1: {player_score}   AI: {cpu_score}", font, white, 200, 10)


        # Если ждём нажатия клавиши, просто выводим текст
        if waiting_for_key:
            draw_text("Press any key to continue...", font, white, screen_width//2, screen_height//2, center=True)
        else:
            # Управление игроками
            if mode == "pvp":
                player_paddle.move(K_w, K_s)
                cpu_paddle.move(K_UP, K_DOWN)
            else:
                player_paddle.move(K_w, K_s)
                cpu_paddle.ai(pong, difficulty)

            # Рисуем объекты
            player_paddle.draw()
            cpu_paddle.draw()
            pong.draw()

            # Бустеры
            booster_timer += 1
            if booster_timer > 300:
                boosters.append(Booster())
                booster_timer = 0
            for b in boosters[:]:
                b.move()
                if b.rect.top > screen_height:
                    boosters.remove(b)
                else:
                    b.draw()

            # Стены (только для hard и AI)
            if mode == "ai" and difficulty == "hard":
                wall_timer += 1
                game_timer += 1
                if wall_timer > random.randint(500, 800):
                    safe_margin = 65
                    for _ in range(random.randint(1, 2)):
                        x = random.randint(safe_margin, screen_width - 95)
                        y = random.randint(80, screen_height - 100)
                        if not any(w.rect.colliderect(Rect(x, y, 30, 80)) for w in walls):
                            walls.append(Wall(x, y, 30, 80, random.choice(["solid","slow","fast"])))
                    wall_timer = 0

            for w in walls[:]:
                w.update()
                w.draw()
                if not w.visible:
                    walls.remove(w)

            # Движение мяча
            winner = pong.move([(player_paddle, "player"), (cpu_paddle, "cpu")], boosters, walls)
            if winner != 0:
                if winner == 1:
                    cpu_score += 1
                    goal_sound.play()
                    draw_text("YOU LOST!", font_big, white, 300, 250, center=True)
                else:
                    player_score += 1
                    lose_sound.play()
                    draw_text("YOU SCORED!", font_big, white, 300, 250, center=True)
                pygame.display.update()
                pygame.time.wait(2000)

                # Сброс мяча и ракеток
                pong = Ball(screen_width // 2, screen_height // 2, 5)
                player_paddle.rect.y = screen_height // 2
                cpu_paddle.rect.y = screen_height // 2

                waiting_for_key = True  # ждём нажатия клавиши перед продолжением

    pygame.display.update()

pygame.quit()
