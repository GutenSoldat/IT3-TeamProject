import pygame
from pygame.locals import *
import random
import math
import os
import glob

pygame.init()
pygame.mixer.init()

# -------------------- ПАРАМЕТРЫ --------------------
screen_width = 600
screen_height = 500
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption('Hotline Pong')
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

# добавляем один экземпляр hover-звука и канал для контроля воспроизведения
hover_sound = pygame.mixer.Sound('zvuk-perezariadki-ak47.mp3')
hover_channel = None

# флаг — последнее взаимодействие было с клавиатуры (используется для звука наведения)
last_input_was_keyboard = False

# добавляем глобальный click_sound и используем его в Button.press
click_sound = pygame.mixer.Sound('odinochn-vystrel-aks.mp3')

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

def fade_while_channel_busy(channel):
    """Показывает плавное затемнение экрана пока играет channel (или хотя бы длительность click_sound)."""
    start = pygame.time.get_ticks()
    duration_ms = int(click_sound.get_length() * 1000)
    overlay = pygame.Surface((screen_width, screen_height))
    overlay.fill((0, 0, 0))
    clock = pygame.time.Clock()

    # Если channel == None — всё равно делаем затемнение по длине click_sound
    while (channel is not None and channel.get_busy()) or (pygame.time.get_ticks() - start < duration_ms):
        elapsed = pygame.time.get_ticks() - start
        progress = min(1.0, elapsed / duration_ms) if duration_ms > 0 else 1.0
        alpha = int(progress * 255)
        overlay.set_alpha(alpha)
        # Наложим поверх текущего экрана
        screen.blit(overlay, (0, 0))
        pygame.display.update()
        clock.tick(60)
    # Гарантируем полностью чёрный финальный кадр перед сменой состояния
    overlay.set_alpha(255)
    screen.blit(overlay, (0, 0))
    pygame.display.update()

def load_background_frames(folder):
    frames = []
    if not os.path.isdir(folder):
        return frames
    names = sorted(os.listdir(folder))
    for name in names:
        path = os.path.join(folder, name)
        try:
            img = pygame.image.load(path).convert()
            img = pygame.transform.scale(img, (screen_width, screen_height))
            frames.append(img)
        except Exception:
            continue
    return frames

def load_sequence_frames(folder, prefix, start, end, digits=3, ext='.jpg'):
    frames = []
    for i in range(start, end + 1):
        name = f"{prefix}{i:0{digits}d}{ext}"
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            # пропускаем отсутствующие файлы, но продолжаем
            continue
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.scale(img, (screen_width, screen_height))
            frames.append(img)
        except Exception:
            continue
    return frames

def run_intro():
    # используем полный путь к папке с кадрами на вашем ПК
    frames = load_background_frames(r'C:\Users\andre\OneDrive\Рабочий стол\Git\GitHubProject\Background')
    try:
        intro_sound = pygame.mixer.Sound('why-did-you-make-me-do-this-made-with-Voicemod.mp3')
    except Exception:
        intro_sound = None

    clock = pygame.time.Clock()
    start = pygame.time.get_ticks()

    # параметры: fade-in 2.5s, звук стартует через 1s, fade-out 4s
    fade_in_ms = 2000
    sound_start_delay = 1000
    fade_out_ms = 1000
    frame_interval = 100  # ms между кадрами анимации

    last_frame_time = start
    fi = 0

    ch = None
    sound_started = False
    sound_start_time = 0
    sound_length_ms = int(intro_sound.get_length() * 1000) if intro_sound else 3000

    running_intro = True
    while running_intro:
        for ev in pygame.event.get():
            if ev.type == QUIT:
                pygame.quit()
                raise SystemExit

        now = pygame.time.get_ticks()
        elapsed = now - start

        # обновляем индекс фрейма анимации (анимация продолжается всегда)
        if frames and (now - last_frame_time) >= frame_interval:
            fi = (fi + 1) % len(frames)
            last_frame_time = now

        # отрисовка текущего фрейма
        if frames:
            screen.blit(frames[fi], (0, 0))
        else:
            screen.fill(background)

        # fade-in: overlay alpha от 255 -> 0 за fade_in_ms
        if elapsed < fade_in_ms:
            progress = elapsed / fade_in_ms
            alpha = int(255 * (1.0 - progress))
        else:
            alpha = 0

        overlay = pygame.Surface((screen_width, screen_height))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(alpha)
        screen.blit(overlay, (0, 0))
        pygame.display.update()
        clock.tick(60)

        # Запуск звука после задержки sound_start_delay (один раз)
        if not sound_started and elapsed >= sound_start_delay:
            if intro_sound:
                ch = intro_sound.play()
                sound_start_time = pygame.time.get_ticks()
            else:
                sound_start_time = pygame.time.get_ticks()
            sound_started = True

        # Если звук стартовал — ждём его окончания, затем делаем fade-out (анимация продолжается)
        if sound_started:
            if ch:
                sound_done = not ch.get_busy()
            else:
                sound_done = (pygame.time.get_ticks() - sound_start_time) >= sound_length_ms

            if sound_done:
                fade_start = pygame.time.get_ticks()
                # подготовим overlay для fade-out
                out_overlay = pygame.Surface((screen_width, screen_height))
                out_overlay.fill((0, 0, 0))
                while True:
                    for ev in pygame.event.get():
                        if ev.type == QUIT:
                            pygame.quit()
                            raise SystemExit

                    tnow = pygame.time.get_ticks()

                    # продолжаем анимацию кадров во время fade-out
                    if frames and (tnow - last_frame_time) >= frame_interval:
                        fi = (fi + 1) % len(frames)
                        last_frame_time = tnow

                    if frames:
                        screen.blit(frames[fi], (0, 0))
                    else:
                        screen.fill(background)

                    t_elapsed = tnow - fade_start
                    progress2 = min(1.0, t_elapsed / fade_out_ms)
                    out_overlay.set_alpha(int(progress2 * 255))
                    screen.blit(out_overlay, (0, 0))
                    pygame.display.update()
                    clock.tick(60)

                    if progress2 >= 1.0:
                        running_intro = False
                        break

# -------------------- КЛАССЫ --------------------
class Button:
    def __init__(self, x, y, w, h, text):
        self.rect = Rect(x, y, w, h)
        self.text = text
        self.hovered_last = False
        self.active_last = False  # запоминаем предыдущее состояние подсветки/наведения
        self.pressed_until = 0  # ms, время окончания эффекта нажатия
        self.press_duration = 120  # длительность эффекта (ms)

        # плавный переход цвета
        self.current_color = white
        self.target_color = white
        self.color_smooth = 0.12  # 0..1 - скорость интерполяции (чем больше, тем быстрее)

        # джиттер в спокойном состоянии
        self.jitter_phase = random.random() * math.pi * 2
        self.jitter_amp = 2.0  # пикселей
        self.jitter_freq = 3.0  # кол-во колебаний в секунду

    def press(self, duration=None):
        # Запуск визуального эффекта нажатия и проигрыш клика
        if duration is None:
            duration = self.press_duration
        self.pressed_until = pygame.time.get_ticks() + duration
        try:
            # играем заранее загруженный click_sound и возвращаем канал
            ch = click_sound.play()
            if ch:
                ch.set_volume(0.5)
            return ch
        except Exception:
            return None

    # добавлен параметр highlight для подсветки при навигации клавиатурой
    def draw(self, highlight=False):
        # теперь игнорируем положение мыши — активность определяется только параметром highlight
        active = bool(highlight)
        now = pygame.time.get_ticks()
        pressed = now < self.pressed_until

        # если активна подсветка — целевой цвет плавно меняется по RGB-циклу (эффект RGB-подсветки)
        if active:
            tsec = now / 1000.0
            freq = 1.0  # частота смены цветов (Hz) — можно увеличить для быстрой смены
            # фазовый сдвиг для R/G/B чтобы получить RGB-циклирование
            r = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + 0.0)))
            g = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + 2.0)))
            b = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + 4.0)))
            self.target_color = (r, g, b)
        else:
            # в спокойном состоянии возвращаемся к белому
            self.target_color = white

        # интерполируем текущий цвет к целевому (плавный переход)
        def lerp_color(a, b, t):
            return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
        self.current_color = lerp_color(self.current_color, self.target_color, self.color_smooth)

        # вычисляем джиттер (только в спокойном состоянии, когда не активна и не нажата)
        jitter_x = jitter_y = 0
        if not active and not pressed:
            tsec = now / 1000.0
            jitter_x = math.sin(tsec * self.jitter_freq + self.jitter_phase) * self.jitter_amp
            # мелкий вертикальный сдвиг с меньшей амплитудой
            jitter_y = math.sin(tsec * (self.jitter_freq * 1.3) + self.jitter_phase * 0.7) * (self.jitter_amp * 0.6)

        # 3D offset: тень смещена, при нажатии тень меньше и прямоугольник смещён вниз-вправо
        shadow_offset = (6, 6) if not pressed else (2, 2)
        press_offset = (0, 0) if not pressed else (2, 2)

        # отрисовка тени (учитываем джиттер)
        shadow_rect = self.rect.move(shadow_offset[0] + int(jitter_x), shadow_offset[1] + int(jitter_y))
        pygame.draw.rect(screen, (30, 30, 30), shadow_rect, border_radius=12)

        # основной цвет (берём текущий интерполированный)
        base_color = self.current_color
        # при нажатии немного затемняем
        if pressed:
            base_color = tuple(max(0, c - 30) for c in base_color)

        # применяем press_offset + джиттер
        draw_rect = self.rect.move(press_offset[0] + int(jitter_x), press_offset[1] + int(jitter_y))
        pygame.draw.rect(screen, base_color, draw_rect, border_radius=10)

        # верхняя/левая подсветка и нижняя/правая тень для объёмного вида
        highlight_color = tuple(min(255, c + 40) for c in base_color)
        pygame.draw.line(screen, highlight_color, (draw_rect.left+4, draw_rect.top+2), (draw_rect.right-4, draw_rect.top+2), 3)
        pygame.draw.line(screen, highlight_color, (draw_rect.left+2, draw_rect.top+4), (draw_rect.left+2, draw_rect.bottom-4), 3)
        dark_color = tuple(max(0, c - 60) for c in base_color)
        pygame.draw.line(screen, dark_color, (draw_rect.left+4, draw_rect.bottom-2), (draw_rect.right-4, draw_rect.bottom-2), 3)
        pygame.draw.line(screen, dark_color, (draw_rect.right-2, draw_rect.top+4), (draw_rect.right-2, draw_rect.bottom-4), 3)

        # текст — сдвигаем при нажатии для ощущения глубины
        text_img = menu_font.render(self.text, True, black)
        text_rect = text_img.get_rect(center=draw_rect.center)
        text_rect = text_rect.move(press_offset[0] + int(jitter_x), press_offset[1] + int(jitter_y))
        screen.blit(text_img, text_rect)

        # Проигрываем звук только при переходе в состояние active через highlight (клавиатура)
        global hover_channel
        if active and not self.active_last and last_input_was_keyboard:
            try:
                if hover_channel is None or not hover_channel.get_busy():
                    hover_channel = hover_sound.play()
                    if hover_channel:
                        hover_channel.set_volume(0.5)
            except Exception:
                pass

        # обновляем состояния для следующего кадра
        self.active_last = active

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class Paddle:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 20, 100)
        self.original_height = self.rect.height
        self.speed = 5
        self.reaction_time = 0
        self.large_until = None  # время окончания увеличения ракетки (ms)

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

    def update(self):
        # если время увеличенной ракетки прошло — вернуть оригинальный размер
        if self.large_until and pygame.time.get_ticks() >= self.large_until:
            center = self.rect.center
            self.rect.height = self.original_height
            self.rect.center = center
            self.large_until = None

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
            # увеличиваем ракетку на 25 пикселей на 5 секунд
            now = pygame.time.get_ticks()
            duration_ms = 5000
            if last_hit == "player":
                p = player_paddle
            else:
                p = cpu_paddle
            # увеличить высоту, сохранив центр
            center = p.rect.center
            p.rect.height = int(p.original_height + 25)
            p.rect.center = center
            p.large_until = now + duration_ms

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

# кнопка Back для меню выбора сложности — справа снизу, 15px от края
btn_back = Button(screen_width - 200 - 15, screen_height - 50 - 15, 200, 50, "Back")

# кнопки, которые отображаются при "Press any key to continue..."
btn_back_pause = Button(screen_width//2 - 200 - 10, screen_height//2 + 60, 200, 50, "Back")
btn_exit_pause = Button(screen_width//2 + 10, screen_height//2 + 60, 200, 50, "Exit")

# индексы для навигации по меню и выбору сложности
menu_index = 0
diff_index = 0
pause_index = 0  # 0 = Back, 1 = Exit (на экране ожидания)

player_paddle = Paddle(20, screen_height // 2)
cpu_paddle = Paddle(screen_width - 40, screen_height // 2)
pong = Ball(screen_width // 2, screen_height // 2, 4)
boosters = []
walls = []
wall_timer = booster_timer = 0
game_timer = 0
mode = "ai"

# очередная генерация стен: список типов, таймер спавна и длительность одной стены
pending_wall_types = []          # очередь типов стен, которые нужно по очереди заспавнить
last_wall_spawn_time = 0         # время последнего спавна из очереди (ms)
wall_spawn_interval = 1500       # интервал между спавнами в очереди (ms) — 1.5 с
wall_lifetime = 1500             # жизнь каждой стены (ms) — 1.5 с

run_intro()
play_music(music_menu)

# загружаем кадры для фона основного меню
backmain_frames = load_sequence_frames(
    r'C:\Users\andre\OneDrive\Рабочий стол\Git\GitHubProject\BackMainMenu',
    prefix='hotline-miami-background_',
    start=0, end=48, digits=3, ext='.jpg'
)
backmain_frame_index = 0
backmain_last_frame_time = pygame.time.get_ticks()
# интервал между кадрами в миллисекундах (40 ms ~= 25 FPS). Поменяйте при желании.
backmain_frame_interval = 40

# Добавляем загрузку кадров для фона меню выбора сложности (63 кадра: 000..062)
backdiff_frames = load_sequence_frames(
    r'C:\Users\andre\OneDrive\Рабочий стол\Git\GitHubProject\BackDifficultyMenu',
    prefix='miamibeach_',
    start=0, end=62, digits=3, ext='.jpg'
)
backdiff_frame_index = 0
backdiff_last_frame_time = pygame.time.get_ticks()
backdiff_frame_interval = 40

running = True
while running:
    fpsClock.tick(fps)
    screen.fill(background)

    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        if event.type == MOUSEBUTTONDOWN:
            # Игнорируем клики: навигация и выбор — только клавиатурой
            last_input_was_keyboard = False
            # не обрабатываем pos и не вызываем is_clicked — клики не должны влиять на кнопки
            continue

            # Если сейчас показывается экран ожидания после гола — обрабатываем Back/Exit
            if waiting_for_key:
                if btn_back_pause.is_clicked(pos):
                    btn_back_pause.press()
                    pygame.display.update()
                    pygame.time.wait(120)
                    # возвращаемся в главное меню, сбрасываем счёт и флаги
                    state = "menu"
                    player_score = cpu_score = 0
                    play_music(music_menu)
                    waiting_for_key = False
                    continue
                if btn_exit_pause.is_clicked(pos):
                    btn_exit_pause.press()
                    pygame.display.update()
                    pygame.time.wait(120)
                    running = False
                    continue

            if state == "menu":
                if btn_ai.is_clicked(pos):
                    btn_ai.press()
                    pygame.display.update()
                    pygame.time.wait(120)
                    state = "difficulty"
                    pygame.mixer.Sound('odinochn-vystrel-aks.mp3').play().set_volume(0.5)
                elif btn_pvp.is_clicked(pos):
                    btn_pvp.press()
                    pygame.display.update()
                    pygame.time.wait(120)
                    mode = "pvp"
                    state = "game"
                    play_music(music_pvp)
                    pygame.mixer.Sound('odinochn-vystrel-aks.mp3').play().set_volume(0.5)
                elif btn_exit.is_clicked(pos):
                    btn_exit.press()
                    pygame.display.update()
                    pygame.time.wait(120)
                    running = False
            elif state == "difficulty":
                if btn_easy.is_clicked(pos):
                    btn_easy.press()
                    pygame.display.update()
                    pygame.time.wait(120)
                    difficulty = "easy"
                    play_music(music_easy)
                    state = "game"
                    pygame.mixer.Sound('odinochn-vystrel-aks.mp3').play().set_volume(0.5)
                elif btn_med.is_clicked(pos):
                    btn_med.press()
                    pygame.display.update()
                    pygame.time.wait(120)
                    difficulty = "medium"
                    play_music(music_medium)
                    state = "game"
                    pygame.mixer.Sound('odinochn-vystrel-aks.mp3').play().set_volume(0.5)
                elif btn_hard.is_clicked(pos):
                    btn_hard.press()
                    pygame.display.update()
                    pygame.time.wait(120)
                    difficulty = "hard"
                    play_music(music_hard)
                    state = "game"
                    pygame.mixer.Sound('odinochn-vystrel-aks.mp3').play().set_volume(0.5)

        # Если ждём нажатия клавиши после гола — обрабатываем специально:
        if waiting_for_key and event.type == KEYDOWN:
            # продолжение игры — только по пробелу
            if event.key == K_SPACE:
                waiting_for_key = False
                # скрываем подсветку кнопок
                last_input_was_keyboard = True
            else:
                # навигация между Back / Exit клавишами A/D
                if event.key == K_a:
                    pause_index = (pause_index - 1) % 2
                    last_input_was_keyboard = True
                elif event.key == K_d:
                    pause_index = (pause_index + 1) % 2
                    last_input_was_keyboard = True
                # Enter — активировать выделенную кнопку
                elif event.key in (K_RETURN, K_KP_ENTER):
                    last_input_was_keyboard = True
                    if pause_index == 0:
                        ch = btn_back_pause.press()
                        pygame.display.update()
                        fade_while_channel_busy(ch)
                        # Back -> в главное меню
                        state = "menu"
                        player_score = cpu_score = 0
                        play_music(music_menu)
                        waiting_for_key = False
                    else:
                        ch = btn_exit_pause.press()
                        pygame.display.update()
                        fade_while_channel_busy(ch)
                        # Exit
                        running = False
            # пропускаем дальнейшую обработку этого KEYDOWN
            continue

        # обработка навигации клавиатурой (W/S и Enter) — только когда не ждём продолжения
        if event.type == KEYDOWN and not waiting_for_key:
            # помечаем, что последнее взаимодействие — клавиатура
            # (звук наведения будет воспроизводиться только если этот флаг True)
            last_input_was_keyboard = True

            # навигация по главному меню
            if state == "menu":
                if event.key in (K_w, K_UP):
                    menu_index = (menu_index - 1) % 3
                elif event.key in (K_s, K_DOWN):
                    menu_index = (menu_index + 1) % 3
                elif event.key in (K_RETURN, K_KP_ENTER):
                    # визуальный эффект нажатия перед переходом
                    if menu_index == 0:
                        btn_ai.press()
                        pygame.display.update()
                        pygame.time.wait(120)
                        state = "difficulty"
                    elif menu_index == 1:
                        btn_pvp.press()
                        pygame.display.update()
                        pygame.time.wait(120)
                        mode = "pvp"
                        state = "game"
                        play_music(music_pvp)
                    elif menu_index == 2:
                        btn_exit.press()
                        pygame.display.update()
                        pygame.time.wait(120)
                        running = False

            # навигация по выбору сложности
            elif state == "difficulty":
                # теперь diff_index может быть 0..3, где 3 = Back
                if event.key in (K_w, K_UP):
                    diff_index = (diff_index - 1) % 4
                elif event.key in (K_s, K_DOWN):
                    diff_index = (diff_index + 1) % 4
                elif event.key in (K_RETURN, K_KP_ENTER):
                    if diff_index == 0:
                        ch = btn_easy.press()
                        pygame.display.update()
                        fade_while_channel_busy(ch)
                        difficulty = "easy"
                        play_music(music_easy)
                        state = "game"
                    elif diff_index == 1:
                        ch = btn_med.press()
                        pygame.display.update()
                        fade_while_channel_busy(ch)
                        difficulty = "medium"
                        play_music(music_medium)
                        state = "game"
                    elif diff_index == 2:
                        ch = btn_hard.press()
                        pygame.display.update()
                        fade_while_channel_busy(ch)
                        difficulty = "hard"
                        play_music(music_hard)
                        state = "game"
                    elif diff_index == 3:
                        # Back через клавиатуру
                        ch = btn_back.press()
                        pygame.display.update()
                        fade_while_channel_busy(ch)
                        state = "menu"
                        pygame.mixer.Sound('odinochn-vystrel-aks.mp3').play().set_volume(0.5)

    # -------------------- МЕНЮ --------------------
    if state == "menu":
        # отрисовка анимированного фона для главного меню (если кадры загружены)
        if backmain_frames:
            now = pygame.time.get_ticks()
            if now - backmain_last_frame_time >= backmain_frame_interval:
                backmain_frame_index = (backmain_frame_index + 1) % len(backmain_frames)
                backmain_last_frame_time = now
            screen.blit(backmain_frames[backmain_frame_index], (0, 0))
        else:
            # fallback — обычный фон
            screen.fill(background)

        menu_timer += 1
        pulse_offset = math.sin(menu_timer * 0.05) * menu_pulse_amplitude
        swing_angle = math.sin(menu_timer * 0.05) * menu_swing_angle
        # Статичная белая надпись убрана — используется по-буквенная RGB-анимация далее
        # text_img = font_big.render("PONG", True, white)
        # text_rect = text_img.get_rect(center=(300, 120 + pulse_offset))
        # rotated_img = pygame.transform.rotate(text_img, swing_angle)
        # rotated_rect = rotated_img.get_rect(center=text_rect.center)
        # screen.blit(rotated_img, rotated_rect)

        # заголовок "PONG" — по-буквенная RGB-переливка с чёрным контуром
        title = "HOTLINE PONG"
        now = pygame.time.get_ticks()
        tsec = now / 1000.0
        letter_surfs = []
        total_w = 0
        max_h = 0
        for i, ch in enumerate(title):
            phase = i * 0.25
            freq = 1.0
            r = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + phase + 0.0)))
            g = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + phase + 2.0)))
            b = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + phase + 4.0)))
            col = (r, g, b)
            color_surf = font_big.render(ch, True, col).convert_alpha()
            bw, bh = color_surf.get_size()
            surf = pygame.Surface((bw + 6, bh + 6), pygame.SRCALPHA)
            black_surf = font_big.render(ch, True, black).convert_alpha()
            offsets = [(-2,0),(2,0),(0,-2),(0,2),(-1,-1),(1,-1),(-1,1),(1,1)]
            for ox, oy in offsets:
                surf.blit(black_surf, (3 + ox, 3 + oy))
            surf.blit(color_surf, (3, 3))
            letter_surfs.append(surf)
            total_w += surf.get_width()
            max_h = max(max_h, surf.get_height())
        text_surf = pygame.Surface((total_w, max_h), pygame.SRCALPHA)
        x = 0
        for surf in letter_surfs:
            text_surf.blit(surf, (x, 0))
            x += surf.get_width()
        rotated_img = pygame.transform.rotate(text_surf, swing_angle)
        rotated_rect = rotated_img.get_rect(center=(300, 120 + pulse_offset))
        screen.blit(rotated_img, rotated_rect)
        # подсвечиваем выбранную кнопку
        btn_ai.draw(highlight=(menu_index==0))
        btn_pvp.draw(highlight=(menu_index==1))
        btn_exit.draw(highlight=(menu_index==2))

    # -------------------- ВЫБОР СЛОЖНОСТИ --------------------
    elif state == "difficulty":
        # отрисовка анимированного фона для меню выбора сложности (если кадры загружены)
        if backdiff_frames:
            now = pygame.time.get_ticks()
            if now - backdiff_last_frame_time >= backdiff_frame_interval:
                backdiff_frame_index = (backdiff_frame_index + 1) % len(backdiff_frames)
                backdiff_last_frame_time = now
            screen.blit(backdiff_frames[backdiff_frame_index], (0, 0))
        else:
            # fallback — обычный фон
            screen.fill(background)

        menu_timer += 1
        pulse_offset = math.sin(menu_timer * 0.05) * menu_pulse_amplitude
        swing_angle = math.sin(menu_timer * 0.05) * menu_swing_angle
        # По-буквенная RGB-подсветка заголовка "Choose Your Way"
        title = "Choose Your Way"
        now = pygame.time.get_ticks()
        tsec = now / 1000.0
        # подготовим поверхности для каждой буквы с индивидуальным цветом и чёрным контуром
        letter_surfs = []
        total_w = 0
        max_h = 0
        for i, ch in enumerate(title):
            # фазовый сдвиг по индексу для красивого градиента
            phase = i * 0.25
            freq = 1.0
            r = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + phase + 0.0)))
            g = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + phase + 2.0)))
            b = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + phase + 4.0)))
            col = (r, g, b)
            # рендерим букву цветом и чёрный контур (несколько смещений)
            color_surf = font_big.render(ch, True, col).convert_alpha()
            bw, bh = color_surf.get_size()
            # создаём поверхность с запасом под контур
            surf = pygame.Surface((bw + 4, bh + 4), pygame.SRCALPHA)
            black_surf = font_big.render(ch, True, black).convert_alpha()
            # смещения для контура (толщина обводки)
            offsets = [(-2,0),(2,0),(0,-2),(0,2),(-1,-1),(1,-1),(-1,1),(1,1)]
            for ox, oy in offsets:
                surf.blit(black_surf, (2 + ox, 2 + oy))
            # центральная цветная буква
            surf.blit(color_surf, (2, 2))
            letter_surfs.append(surf)
            total_w += surf.get_width()
            max_h = max(max_h, surf.get_height())
        # соберём строку в прозрачную поверхность
        text_surf = pygame.Surface((total_w, max_h), pygame.SRCALPHA)
        x = 0
        for surf in letter_surfs:
            text_surf.blit(surf, (x, 0))
            x += surf.get_width()
        # поворот и центрирование как раньше
        rotated_img = pygame.transform.rotate(text_surf, swing_angle)
        rotated_rect = rotated_img.get_rect(center=(300, 120 + pulse_offset))
        screen.blit(rotated_img, rotated_rect)
        # подсвечиваем выбранную кнопку сложности
        btn_easy.draw(highlight=(diff_index==0))
        btn_med.draw(highlight=(diff_index==1))
        btn_hard.draw(highlight=(diff_index==2))
        # рисуем Back справа-снизу (можно навестись клавиатурой)
        btn_back.draw(highlight=(diff_index==3))

    # -------------------- ИГРА --------------------
    elif state == "game":
        draw_board()
        if mode == "pvp":
            draw_text(f"P1: {player_score}   P2: {cpu_score}", font, white, 200, 10)
        else:  # против ИИ
            draw_text(f"P1: {player_score}   AI: {cpu_score}", font, white, 200, 10)


        # Если ждём нажатия клавиши, просто выводим текст
        if waiting_for_key:
            draw_text("Press SPACE to continue...", font, white, screen_width//2, screen_height//2, center=True)
            # рисуем кнопки Back и Exit под текстом (подсветка по pause_index)
            btn_back_pause.draw(highlight=(pause_index==0))
            btn_exit_pause.draw(highlight=(pause_index==1))
        else:
            # Управление игроками
            if mode == "pvp":
                player_paddle.move(K_w, K_s)
                cpu_paddle.move(K_UP, K_DOWN)
            else:
                player_paddle.move(K_w, K_s)
                cpu_paddle.ai(pong, difficulty)

            # обновляем состояния ракеток (в т.ч. таймеры увеличения)
            player_paddle.update()
            cpu_paddle.update()

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

            # Стены: появляются в режиме PVP или в AI при difficulty == "hard"
            if (mode == "ai" and difficulty == "hard") or mode == "pvp":
                wall_timer += 1
                game_timer += 1

                # Когда таймер достигает порога — сформировать очередь типов стен (не спавнить сразу)
                if wall_timer > random.randint(500, 800) and not pending_wall_types:
                    safe_margin = 65
                    solids = random.randint(2, 3)   # красные отражающие
                    slows = random.randint(1, 2)    # жёлтые замедляющие
                    fasts = random.randint(1, 3)    # зелёные ускоряющие
                    types = ["solid"] * solids + ["slow"] * slows + ["fast"] * fasts
                    random.shuffle(types)
                    pending_wall_types = types[:]  # заполнили очередь
                    # подготовим момент для немедленного спавна первой стены
                    last_wall_spawn_time = pygame.time.get_ticks() - wall_spawn_interval
                    # обнуляем основной таймер, чтобы через время снова сформировать очередь
                    wall_timer = 0

                # Спавним по одному элементу из очереди с интервалом wall_spawn_interval
                if pending_wall_types and pygame.time.get_ticks() - last_wall_spawn_time >= wall_spawn_interval:
                    t = pending_wall_types.pop(0)
                    placed = False
                    attempts = 0
                    safe_margin = 65
                    while not placed and attempts < 30:
                        x = random.randint(safe_margin, screen_width - 95)
                        y = random.randint(80, screen_height - 100)
                        new_rect = Rect(x, y, 30, 80)
                        if not any(w.rect.colliderect(new_rect.inflate(10, 10)) for w in walls):
                            w = Wall(x, y, 30, 80, t)
                            # задаём время жизни каждой стены wall_lifetime (1.5s)
                            w.duration = wall_lifetime
                            walls.append(w)
                            placed = True
                        attempts += 1
                    last_wall_spawn_time = pygame.time.get_ticks()

            for w in walls[:]:
                w.update()
                w.draw()
                if not w.visible:
                    walls.remove(w)

            # Движение мяча
            winner = pong.move([(player_paddle, "player"), (cpu_paddle, "cpu")], boosters, walls)
            if winner != 0:
                waiting_for_key = True  # ждём нажатия клавиши перед продолжением
                cpu_paddle.rect.y = screen_height // 2
                player_paddle.rect.y = screen_height // 2
                pong = Ball(screen_width // 2, screen_height // 2, 5)
                # Сброс мяча и ракеток
                pygame.time.wait(100)
                pygame.display.update()
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