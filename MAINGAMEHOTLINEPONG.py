import pygame
from pygame.locals import *
import random
import math
import os
import glob

# базовая папка — папка, где лежит этот скрипт; позволяет перемещать проект без правки путей
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def res(rel_path):
    return os.path.join(BASE_DIR, rel_path)

pygame.init()
# Инициализация микшера с безопасным фолбеком
sound_enabled = True
try:
    pygame.mixer.init()
except Exception:
    sound_enabled = False

# -------------------- ПАРАМЕТРЫ --------------------
screen_width = 600
screen_height = 500
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption('Hotline Pong')
icon = pygame.image.load(res('wellwellwell8.jpg'))
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
# Шрифт с фолбеком на системный, если файл отсутствует
try:
    font = pygame.font.Font(res('fonts/Squealer.otf'), 36)
    font_big = pygame.font.Font(res('fonts/Squealer.otf'), 72)
    menu_font = pygame.font.Font(res('fonts/Squealer.otf'), 42)
except Exception:
    font = pygame.font.SysFont(None, 36)
    font_big = pygame.font.SysFont(None, 72)
    menu_font = pygame.font.SysFont(None, 42)

# Пульсация меню
menu_timer = 0
menu_pulse_amplitude = 10
menu_swing_angle = 5

# игровая область (бордера). Верхняя линия уже была на y=50 — добавляем нижнюю симметрично
top_border_y = 50
bottom_border_y = screen_height - 50

# Музыка
music_menu = res('music/Sun Araw - Horse Steppin _ Hotline Miami OST.mp3')
music_easy = res('music/Hotline Miami Soundtrack ~ Crystals [QXkSYSPTpj4].mp3')
music_medium = res('music/Perturbator - Miami Disco _ Hotline Miami OST.mp3')
music_hard = res('music/Jasper Byrne - Hotline _ Hotline Miami OST.mp3')
music_pvp = res('music/Perturbator - Vengance _ Hotline Miami OST.mp3')
if sound_enabled:
    try:
        goal_sound = pygame.mixer.Sound(res('music/Windows Error Sound effect.mp3'))
    except Exception:
        goal_sound = None
    try:
        lose_sound = pygame.mixer.Sound(res('music/GOAL.mp3'))
    except Exception:
        lose_sound = None
else:
    goal_sound = None
    lose_sound = None

# добавляем один экземпляр hover-звука и канал для контроля воспроизведения
if sound_enabled:
    try:
        hover_sound = pygame.mixer.Sound(res('music/zvuk-perezariadki-ak47.mp3'))
    except Exception:
        hover_sound = None
else:
    hover_sound = None
hover_channel = None

# флаг — последнее взаимодействие было с клавиатуры (используется для звука наведения)
last_input_was_keyboard = False

# добавляем глобальный click_sound и используем его в Button.press
if sound_enabled:
    try:
        click_sound = pygame.mixer.Sound(res('music/odinochn-vystrel-aks.mp3'))
    except Exception:
        click_sound = None
else:
    click_sound = None

# -------------------- ФУНКЦИИ --------------------
def play_music(track):
    if not sound_enabled:
        return
    try:
        pygame.mixer.music.load(track)
        pygame.mixer.music.play(-1)
        # Use settings_volume if available so UI slider affects all music
        vol = globals().get('settings_volume', 0.2)
        try:
            pygame.mixer.music.set_volume(vol)
        except Exception:
            # fallback to default
            try:
                pygame.mixer.music.set_volume(0.2)
            except Exception:
                pass
    except Exception:
        pass

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
    # верхний бордер (разделитель для HUD)
    pygame.draw.line(screen, white, (0, top_border_y), (screen_width, top_border_y))
    # нижний бордер — от которого мяч будет отскакивать, чтобы не проваливался
    pygame.draw.line(screen, white, (0, bottom_border_y), (screen_width, bottom_border_y))

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

def difficulty_ball_speed(diff):
    # Возвращает базовую скорость мяча для данной сложности.
    if diff == "easy":
        return 4
    if diff == "medium":
        return 5
    if diff == "hard":
        return 6
    # по умолчанию (PVP или неопределённая) — средняя
    return 5

def run_intro():
    # используем папку Background внутри проекта
    frames = load_background_frames(res('Background'))
    try:
        intro_sound = pygame.mixer.Sound(res('music/why-did-you-make-me-do-this-made-with-Voicemod.mp3'))
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
    def __init__(self, x, y, w, h, text, image_path=None):
        self.rect = Rect(x, y, w, h)
        self.text = text
        # Поддержка кнопок с изображением (иконка в центре)
        self.image = None
        if image_path:
            try:
                img = pygame.image.load(image_path).convert_alpha()
                img = pygame.transform.smoothscale(img, (max(8, w-12), max(8, h-12)))
                self.image = img
            except Exception:
                self.image = None
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
            if click_sound:
                ch = click_sound.play()
                if ch:
                    ch.set_volume(0.5)
                return ch
        except Exception:
            pass
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

        # Если есть картинка — показываем её центрированной на кнопке
        if self.image:
            img_rect = self.image.get_rect(center=draw_rect.center)
            img_rect = img_rect.move(press_offset[0] + int(jitter_x), press_offset[1] + int(jitter_y))
            screen.blit(self.image, img_rect)
        else:
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
        # лимитирование по верхнему/нижнему бордеру
        if keys[up_key] and self.rect.top > top_border_y:
            self.rect.move_ip(0, -self.speed)
        if keys[down_key] and self.rect.bottom < bottom_border_y:
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
        if self.rect.centery < ball.rect.top and self.rect.bottom < bottom_border_y:
            self.rect.move_ip(0, int(self.speed * speed_factor))
        elif self.rect.centery > ball.rect.bottom and self.rect.top > top_border_y:
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

    def _reflect_from_paddle(self, p, name):
        """Устанавливает new velocity в зависимости от места попадания по высоте."""
        # hit ratio: -1 (верх) .. 0 (центр) .. 1 (низ)
        hit_ratio = (self.rect.centery - p.rect.centery) / (p.rect.height / 2)
        hit_ratio = max(-1.0, min(1.0, hit_ratio))
        max_angle = math.radians(80)  # максимум угла отклонения от горизонтали
        angle = hit_ratio * max_angle
        # Небольшой рандом рядом с центром, чтобы мяч не летел идеально по горизонтали
        if abs(hit_ratio) < 0.12:
            angle += random.uniform(-0.15, 0.15) * max_angle
        # сохраняем текущую скорость как величину
        mag = max(1.0, math.hypot(self.speed_x, self.speed_y))
        # направление по X: отталкиваемся от ракетки (вправо для левой ракетки, влево для правой)
        dir_sign = 1 if p.rect.centerx < screen_width / 2 else -1
        # устанавливаем новые компоненты скорости (исходные)
        sx = math.cos(angle) * mag * dir_sign
        sy = math.sin(angle) * mag

        # Гарантируем минимум вертикальной составляющей, чтобы не было скучных идеально горизонтальных отскоков
        min_vert_ratio = 0.15
        min_vert = mag * min_vert_ratio
        if abs(sy) < min_vert:
            sy = math.copysign(min_vert, sy if sy != 0 else random.choice([-1, 1]))
            sx_mag = math.sqrt(max(0.0, mag * mag - sy * sy))
            sx = math.copysign(sx_mag, sx if sx != 0 else dir_sign)

        # Также сохраняем прежнюю защиту от чисто вертикальных отскоков
        min_horz_ratio = 0.5  # доля от общей скорости
        min_horz = mag * min_horz_ratio
        if abs(sx) < min_horz:
            sx = math.copysign(min_horz, sx if sx != 0 else dir_sign)
            sy_sign = math.copysign(1.0, sy) if sy != 0 else 1.0
            sy = sy_sign * math.sqrt(max(0.0, mag * mag - sx * sx))

        self.speed_x = sx
        self.speed_y = sy
        self.last_hit = name

    def move(self, paddles, boosters, walls):
        # Восстановление стандартной скорости, если эффект закончился
        if self.effect_end_time and pygame.time.get_ticks() >= self.effect_end_time:
            self.speed_x = (self.initial_speed_x if self.speed_x > 0 else -self.initial_speed_x)
            self.speed_y = (self.initial_speed_y if self.speed_y > 0 else -self.initial_speed_y)
            self.effect_end_time = None

        # сначала двигаем по X и проверяем горизонтальные столкновения (ракеты / стены)
        self.rect.x += int(self.speed_x)

        # Столкновения с ракетками (горизонтально) — корректируем позицию и отражаем по X
        for p, name in paddles:
            if self.rect.colliderect(p.rect):
                # поместить мяч рядом с ракеткой по X в зависимости от направления
                if self.speed_x > 0:
                    # двигались вправо -> упёрлись в левую грань ракетки
                    self.rect.right = p.rect.left
                else:
                    self.rect.left = p.rect.right
                # Вводим реалистичный отскок в зависимости от места попадания
                try:
                    self._reflect_from_paddle(p, name)
                except Exception:
                    # fallback — простое инвертирование
                    self.speed_x = -self.speed_x
                    self.last_hit = name

        # Столкновения со стенами (горизонтально) — корректируем позицию и применяем эффект
        for w in walls:
            if w.visible and self.rect.colliderect(w.rect) and not getattr(w, 'used', False):
                w.used = True
                # ставим мяч снаружи стены по X
                if self.rect.centerx < w.rect.centerx:
                    self.rect.right = w.rect.left
                else:
                    self.rect.left = w.rect.right

                if w.type == "solid":
                    self.speed_x = -self.speed_x
                elif w.type == "slow":
                    self.speed_x = int(self.speed_x * 0.6) or (-1 if self.speed_x < 0 else 1)
                    self.speed_y = int(self.speed_y * 0.6) or (-1 if self.speed_y < 0 else 1)
                    self.effect_end_time = pygame.time.get_ticks() + 4000
                elif w.type == "fast":
                    self.speed_x = int(self.speed_x * 1.2) or (1 if self.speed_x > 0 else -1)
                    self.speed_y = int(self.speed_y * 1.2) or (1 if self.speed_y > 0 else -1)
                    self.effect_end_time = pygame.time.get_ticks() + 4000

        # затем двигаем по Y и проверяем вертикальные столкновения (границы / ракетки / стены)
        self.rect.y += int(self.speed_y)

        # Отскок от верхней и нижней границы — корректируем позицию и скорость
        if self.rect.top < top_border_y:
            self.rect.top = top_border_y
            self.speed_y = abs(self.speed_y)
        elif self.rect.bottom > bottom_border_y:
            self.rect.bottom = bottom_border_y
            self.speed_y = -abs(self.speed_y)

        # Столкновения с ракетками (вертикально) — если мяч всё ещё пересекает ракетку по Y, делаем отражение с учётом места попадания
        for p, name in paddles:
            if self.rect.colliderect(p.rect):
                # выталкиваем по вертикали чтобы убрать проникновение
                if self.speed_y > 0:
                    self.rect.bottom = p.rect.top
                else:
                    self.rect.top = p.rect.bottom
                # отражаем с расчётом угла по месту попадания
                try:
                    self._reflect_from_paddle(p, name)
                except Exception:
                    self.speed_y = -self.speed_y
                    self.last_hit = name

        # Взаимодействие с бустерами (после движения)
        for b in boosters[:]:
            if self.rect.colliderect(b.rect) and not b.used:
                b.activate(self, self.last_hit)
                try:
                    boosters.remove(b)
                except ValueError:
                    pass
                pygame.time.set_timer(pygame.USEREVENT + 1, 2000)

        # Взаимодействие со стенами по вертикали — если мяч "вошёл" в стену по Y, выталкиваем и обрабатываем эффект
        for w in walls:
            if w.visible and self.rect.colliderect(w.rect) and not getattr(w, 'used', False):
                w.used = True
                # выталкиваем сверху/снизу
                if self.rect.centery < w.rect.centery:
                    self.rect.bottom = w.rect.top
                else:
                    self.rect.top = w.rect.bottom

                if w.type == "solid":
                    self.speed_y = -self.speed_y
                elif w.type == "slow":
                    self.speed_x = int(self.speed_x * 0.6) or (-1 if self.speed_x < 0 else 1)
                    self.speed_y = int(self.speed_y * 0.6) or (-1 if self.speed_y < 0 else 1)
                    self.effect_end_time = pygame.time.get_ticks() + 4000
                elif w.type == "fast":
                    self.speed_x = int(self.speed_x * 1.2) or (1 if self.speed_x > 0 else -1)
                    self.speed_y = int(self.speed_y * 1.2) or (1 if self.speed_y > 0 else -1)
                    self.effect_end_time = pygame.time.get_ticks() + 4000

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
        # спавн по Y у верхней границы игрового поля
        self.rect = Rect(random.randint(50, screen_width - 70), top_border_y, 20, 20)
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

# центр игровой области с учётом бордеров — используем везде для корректного позиционирования
center_y = (top_border_y + bottom_border_y) // 2
player_paddle = Paddle(20, center_y)
cpu_paddle = Paddle(screen_width - 40, center_y)
pong = Ball(screen_width // 2, center_y, 4)
boosters = []
walls = []
wall_timer = booster_timer = 0
game_timer = 0
mode = "ai"

# -------------------- SETTINGS UI --------------------
# кнопка-шестерёнка в правом нижнем углу (квадрат)
settings_icon_size = 70
btn_settings = Button(screen_width - settings_icon_size - 15, screen_height - settings_icon_size - 15,
                      settings_icon_size, settings_icon_size, "", image_path=res('Shesternya.png'))

# звук/громкость
if sound_enabled:
    try:
        settings_volume = pygame.mixer.music.get_volume()
    except Exception:
        settings_volume = 0.2
else:
    settings_volume = 0.2

# слайдер параметры
slider_width = 380
slider_height = 34
slider_rect = pygame.Rect((screen_width - slider_width) // 2, screen_height // 2, slider_width, slider_height)
slider_dragging = False

# sparkle (звёздочки) для фоновой анимации
class Sparkle:
    def __init__(self):
        self.x = random.randint(0, screen_width-1)
        self.y = random.randint(0, screen_height-1)
        self.life = random.randint(500, 2000)
        self.spawn = pygame.time.get_ticks()
        self.size = random.randint(1, 3)
        self.brightness = random.uniform(0.4, 1.0)

    def draw(self):
        age = pygame.time.get_ticks() - self.spawn
        t = max(0.0, min(1.0, age / self.life))
        a = int(255 * (1.0 - t) * self.brightness)
        surf = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        surf.fill((255,255,255,a))
        screen.blit(surf, (self.x, self.y))

    def is_dead(self):
        return pygame.time.get_ticks() - self.spawn >= self.life

settings_sparkles = []
sparkle_timer = 0

# очередная генерация стен: список типов, таймер спавна и длительность одной стены
pending_wall_types = []          # очередь типов стен, которые нужно по очереди заспавнить
last_wall_spawn_time = 0         # время последнего спавна из очереди (ms)
wall_spawn_interval = 1500       # интервал между спавнами в очереди (ms) — 1.5 с
wall_lifetime = 1500             # жизнь каждой стены (ms) — 1.5 с

run_intro()
play_music(music_menu)

# загружаем кадры для фона основного меню
backmain_frames = load_sequence_frames(
    res('BackMainMenu'),
    prefix='hotline-miami-background_',
    start=0, end=48, digits=3, ext='.jpg'
)
backmain_frame_index = 0
backmain_last_frame_time = pygame.time.get_ticks()
# интервал между кадрами в миллисекундах (40 ms ~= 25 FPS). Поменяйте при желании.
backmain_frame_interval = 40

# Добавляем загрузку кадров для фона меню выбора сложности (63 кадра: 000..062)
backdiff_frames = load_sequence_frames(
    res('BackDifficultyMenu'),
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
            # мышь не управляет меню — только клавиатура/стрелки.
            # Однако внутри экрана настроек разрешаем перетаскивать слайдер мышью.
            last_input_was_keyboard = False
            pos = event.pos
            if state == "settings":
                # проверим, кликнули ли по дорожке или по кнопке
                knob_x = slider_rect.left + int(settings_volume * slider_rect.width)
                knob_rect = pygame.Rect(0, 0, slider_height+6, slider_height+6)
                knob_rect.center = (knob_x, slider_rect.centery)
                if knob_rect.collidepoint(pos) or slider_rect.collidepoint(pos):
                    slider_dragging = True
                    rel = (pos[0] - slider_rect.left) / float(slider_rect.width)
                    settings_volume = max(0.0, min(1.0, rel))
                    if sound_enabled:
                        try:
                            pygame.mixer.music.set_volume(settings_volume)
                        except Exception:
                            pass
                continue

        if event.type == MOUSEMOTION:
            if slider_dragging and state == "settings":
                mx, my = event.pos
                rel = (mx - slider_rect.left) / float(slider_rect.width)
                settings_volume = max(0.0, min(1.0, rel))
                if sound_enabled:
                    try:
                        pygame.mixer.music.set_volume(settings_volume)
                    except Exception:
                        pass

        if event.type == MOUSEBUTTONUP:
            if slider_dragging:
                slider_dragging = False

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

            # Если мы в меню настроек — обрабатываем клавиши тут (ESC — назад, стрелки — громкость)
            if state == "settings":
                if event.key == K_ESCAPE:
                    state = "menu"
                    last_input_was_keyboard = True
                    continue
                if event.key in (K_LEFT, K_a):
                    settings_volume = max(0.0, settings_volume - 0.05)
                    if sound_enabled:
                        try:
                            pygame.mixer.music.set_volume(settings_volume)
                        except Exception:
                            pass
                    continue
                if event.key in (K_RIGHT, K_d):
                    settings_volume = min(1.0, settings_volume + 0.05)
                    if sound_enabled:
                        try:
                            pygame.mixer.music.set_volume(settings_volume)
                        except Exception:
                            pass
                    continue

            # навигация по главному меню
            if state == "menu":
                if event.key in (K_w, K_UP):
                    menu_index = (menu_index - 1) % 4
                elif event.key in (K_s, K_DOWN):
                    menu_index = (menu_index + 1) % 4
                elif event.key in (K_RETURN, K_KP_ENTER):
                    # визуальный эффект нажатия перед переходом
                    if menu_index == 0:
                        btn_ai.press()
                        pygame.display.update()
                        pygame.time.wait(120)
                        # гарантируем режим AI при входе в выбор сложности
                        mode = "ai"
                        state = "difficulty"
                    elif menu_index == 1:
                        btn_pvp.press()
                        pygame.display.update()
                        pygame.time.wait(120)
                        mode = "pvp"
                        # создаём мяч для PVP со стандартной скоростью PVP (используем среднюю)
                        pong = Ball(screen_width // 2, screen_height // 2, difficulty_ball_speed(None))
                        state = "game"
                        play_music(music_pvp)
                    elif menu_index == 2:
                        btn_exit.press()
                        pygame.display.update()
                        pygame.time.wait(120)
                        running = False
                    elif menu_index == 3:
                        # открыть меню настроек
                        btn_settings.press()
                        pygame.display.update()
                        pygame.time.wait(120)
                        state = "settings"

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
                        # явно переключаем режим на AI при старте игры из меню сложности
                        mode = "ai"
                        difficulty = "easy"
                        play_music(music_easy)
                        state = "game"
                    elif diff_index == 1:
                        ch = btn_med.press()
                        pygame.display.update()
                        fade_while_channel_busy(ch)
                        mode = "ai"
                        difficulty = "medium"
                        play_music(music_medium)
                        state = "game"
                    elif diff_index == 2:
                        ch = btn_hard.press()
                        pygame.display.update()
                        fade_while_channel_busy(ch)
                        mode = "ai"
                        difficulty = "hard"
                        play_music(music_hard)
                        # пересоздаём мяч с базовой скоростью для выбранной сложности
                        pong = Ball(screen_width // 2, screen_height // 2, difficulty_ball_speed(difficulty))
                        state = "game"
                    elif diff_index == 3:
                        # Back через клавиатуру
                        ch = btn_back.press()
                        pygame.display.update()
                        fade_while_channel_busy(ch)
                        state = "menu"
                        if click_sound:
                            try:
                                click_sound.play().set_volume(0.5)
                            except Exception:
                                pass

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
        # settings cog in menu (styled like others)
        btn_settings.draw(highlight=(menu_index==3))

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

    # -------------------- НАСТРОЙКИ --------------------
    elif state == "settings":
        # полностью чёрный фон с редкими переливами-пикселями (звёзды)
        screen.fill(black)
        # спавним редкие искорки
        sparkle_timer += 2
        if random.random() < 0.3:
            settings_sparkles.append(Sparkle())
        # обновляем и рисуем искорки
        for s in settings_sparkles[:]:
            s.draw()
            if s.is_dead():
                try:
                    settings_sparkles.remove(s)
                except ValueError:
                    pass

        # Заголовок
        draw_text("SETTINGS", font_big, white, screen_width//2, 80, center=True)

        # Дорожка слайдера (мягко-белого цвета)
        track_color = (240, 240, 240)
        pygame.draw.rect(screen, (40,40,40), slider_rect.inflate(8,8), border_radius=slider_height//2+4)
        pygame.draw.rect(screen, track_color, slider_rect, border_radius=slider_height//2)

        # Кнопка-ручка: изображаем как "Сатурн" — шар и кольцо
        knob_x = slider_rect.left + int(settings_volume * slider_rect.width)
        knob_y = slider_rect.centery
        knob_r = slider_height//2 + 6
        # кольцо (эллипс немного шире чем шар)
        ring_rect = pygame.Rect(0,0, int(knob_r*3), int(knob_r*1.0))
        ring_rect.center = (knob_x, knob_y)
        pygame.draw.ellipse(screen, (200,180,140,180), ring_rect, width=6)
        # сам шар
        pygame.draw.circle(screen, (180,140,90), (knob_x, knob_y), knob_r)
        # небольшой блик
        pygame.draw.circle(screen, (255,220,180), (knob_x - knob_r//3, knob_y - knob_r//3), max(1, knob_r//5))

        # Текст и инструкция
        draw_text("Music Volume", font, (200,200,200), screen_width//2, slider_rect.top - 30, center=True)
        draw_text("Press ESC to return", font, (150,150,150), screen_width//2, slider_rect.bottom + 40, center=True)

        # Рисуем кнопку шестерёнки (чтобы пользователь видел куда нажимал)
        # btn_settings.draw()

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
                # удаляем бустер, если он ушёл за нижний бордер
                if b.rect.top > bottom_border_y:
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
                # выравниваем по центру игровой области
                cpu_paddle.rect.centery = center_y
                player_paddle.rect.centery = center_y
                pong = Ball(screen_width // 2, center_y, 5)
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
                # создаём новый мяч: если режим AI — скорость по выбранной сложности, иначе средняя
                new_speed = difficulty_ball_speed(difficulty) if mode == "ai" and difficulty else difficulty_ball_speed(None)
                pong = Ball(screen_width // 2, center_y, new_speed)
                player_paddle.rect.centery = center_y
                cpu_paddle.rect.centery = center_y

                waiting_for_key = True  # ждём нажатия клавиши перед продолжением


    pygame.display.update()

pygame.quit()