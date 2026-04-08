import pygame
from pygame.locals import *
import json
import random
import math
import os
import glob

# базова папка — папка, де лежить цей скрипт; дозволяє переміщувати проект без правки шляхів
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def res(rel_path):
    return os.path.join(BASE_DIR, rel_path)

pygame.init()
# Ініціалізація мікшера з безпечним фолбеком
sound_enabled = True
try:
    pygame.mixer.init()
except Exception:
    sound_enabled = False

# Попередження про відсутність гарнітури / аудіопристрою (нефатальна помилка).
# Якщо аудіопідсистема не доступна — показуємо неблокуюче повідомлення
# внизу зліва. Повідомлення відображається `HEADSET_WARNING_DISPLAY` мс,
# після чого починається затемнення протягом `HEADSET_WARNING_FADE` мс.
HEADSET_WARNING_DISPLAY = 7000  # ms (час показу до початку затемнення)
HEADSET_WARNING_FADE = 700      # ms (тривалість ефекту затемнення)
headset_warning = False
headset_warning_start = None
if not sound_enabled:
    try:
        # Безпечно викликати get_ticks() після pygame.init()
        headset_warning = True
        headset_warning_start = pygame.time.get_ticks()
    except Exception:
        headset_warning = False

# -------------------- ПАРАМЕТРИ --------------------
screen_width = 600
screen_height = 500
# Розміри реального вікна (можуть змінюватись при зміні режиму)
window_width = screen_width
window_height = screen_height
# Створюємо реальне вікно, але всі відрисовки ведемо у віртуальну поверхню `screen`
real_screen = pygame.display.set_mode((window_width, window_height))
pygame.display.set_caption('Hotline Pong')
icon = pygame.image.load(res('wellwellwell8.jpg'))
pygame.display.set_icon(icon)
# Віртуальна поверхня (логічна роздільна здатність гри). Малюємо сюди,
# потім масштабуватимемо на `real_screen` так, щоб всі елементи зберігали пропорції.
screen = pygame.Surface((screen_width, screen_height))

# Кольори
background = (50, 25, 50)
white = (255, 255, 255)
black = (0, 0, 0)
gray = (180, 180, 180)
red = (255, 50, 50)
yellow = (255, 255, 0)
green = (0, 255, 0)

# Шрифти
# Шрифт з фолбеком на системний, якщо файл відсутній
try:
    font = pygame.font.Font(res('fonts/Squealer.otf'), 36)
    font_big = pygame.font.Font(res('fonts/Squealer.otf'), 72)
    menu_font = pygame.font.Font(res('fonts/Squealer.otf'), 42)
except Exception:
    font = pygame.font.SysFont(None, 36)
    font_big = pygame.font.SysFont(None, 72)
    menu_font = pygame.font.SysFont(None, 42)

# Пульсація меню
menu_timer = 0
menu_pulse_amplitude = 10
menu_swing_angle = 5

# ігрова область (бордери). Верхня лінія — y=50, додаємо нижню симетрично
top_border_y = 50
bottom_border_y = screen_height - 50

# Музика
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

# додаємо один екземпляр hover-звуку та канал для контролю відтворення
if sound_enabled:
    try:
        hover_sound = pygame.mixer.Sound(res('music/zvuk-perezariadki-ak47.mp3'))
    except Exception:
        hover_sound = None
else:
    hover_sound = None
hover_channel = None

# прапорець — остання взаємодія була з клавіатури (використовується для звуку наведення)
last_input_was_keyboard = False

# додаємо глобальний click_sound і використовуємо його в Button.press
if sound_enabled:
    try:
        click_sound = pygame.mixer.Sound(res('music/odinochn-vystrel-aks.mp3'))
    except Exception:
        click_sound = None
else:
    click_sound = None

# -------------------- ФУНКЦІЇ --------------------
def play_music(track):
    if not sound_enabled:
        return
    try:
        pygame.mixer.music.load(track)
        pygame.mixer.music.play(-1)
        # Використовуємо settings_volume, якщо він є, щоб слайдер впливав на музику
        vol = globals().get('settings_volume', 0.2)
        try:
            pygame.mixer.music.set_volume(vol)
        except Exception:
            # запасний варіант на випадок помилки
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
    # верхній бордер (роздільник для HUD)
    pygame.draw.line(screen, white, (0, top_border_y), (screen_width, top_border_y))
    # нижній бордер — від якого м'яч буде відскакувати, щоб не провалювався
    pygame.draw.line(screen, white, (0, bottom_border_y), (screen_width, bottom_border_y))

def fade_while_channel_busy(channel):
    """Показує плавне затемнення екрану поки відтворюється channel (або принаймні довжина click_sound)."""
    start = pygame.time.get_ticks()
    duration_ms = int(click_sound.get_length() * 1000)
    overlay = pygame.Surface((screen_width, screen_height))
    overlay.fill((0, 0, 0))
    clock = pygame.time.Clock()

    # Якщо channel == None — все одно робимо затемнення за довжиною click_sound
    while (channel is not None and channel.get_busy()) or (pygame.time.get_ticks() - start < duration_ms):
        elapsed = pygame.time.get_ticks() - start
        progress = min(1.0, elapsed / duration_ms) if duration_ms > 0 else 1.0
        alpha = int(progress * 255)
        overlay.set_alpha(alpha)
        # Накладаємо поверх поточного екрану
        screen.blit(overlay, (0, 0))
        present()
        clock.tick(60)
    # Гарантуємо повністю чорний фінальний кадр перед зміною стану
    overlay.set_alpha(255)
    screen.blit(overlay, (0, 0))
    # Масштабуємо віртуальну поверхню `screen` на реальний екран `real_screen`
    try:
        scaled = pygame.transform.smoothscale(screen, (window_width, window_height))
        real_screen.blit(scaled, (0, 0))
        present()
    except Exception:
        # fallback
        present()

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
            # пропускаємо відсутні файли, але продовжуємо
            continue
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.scale(img, (screen_width, screen_height))
            frames.append(img)
        except Exception:
            continue
    return frames

def difficulty_ball_speed(diff):
    # Повертає базову швидкість м'яча для даної складності.
    if diff == "easy":
        return 4
    if diff == "medium":
        return 5
    if diff == "hard":
        return 6
    # за замовчуванням (PVP або невизначена) — середня
    return 5

def run_intro():
    # використовуємо папку Background всередині проєкту
    frames = load_background_frames(res('Background'))
    try:
        intro_sound = pygame.mixer.Sound(res('music/why-did-you-make-me-do-this-made-with-Voicemod.mp3'))
    except Exception:
        intro_sound = None

    clock = pygame.time.Clock()
    start = pygame.time.get_ticks()

    # параметри: fade-in 2.5s, звук стартує через 1s, fade-out 4s
    fade_in_ms = 2000
    sound_start_delay = 1000
    fade_out_ms = 1000
    frame_interval = 100  # ms між кадрами анімації

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

        # оновлюємо індекс кадру анімації (анімація триває завжди)
        if frames and (now - last_frame_time) >= frame_interval:
            fi = (fi + 1) % len(frames)
            last_frame_time = now

        # відмалюємо поточний кадр
        if frames:
            screen.blit(frames[fi], (0, 0))
        else:
            screen.fill(background)

        # fade-in: overlay alpha від 255 -> 0 за fade_in_ms
        if elapsed < fade_in_ms:
            progress = elapsed / fade_in_ms
            alpha = int(255 * (1.0 - progress))
        else:
            alpha = 0

        overlay = pygame.Surface((screen_width, screen_height))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(alpha)
        screen.blit(overlay, (0, 0))
        present()
        clock.tick(60)

        # Запуск звуку після затримки sound_start_delay (один раз)
        if not sound_started and elapsed >= sound_start_delay:
            if intro_sound:
                ch = intro_sound.play()
                sound_start_time = pygame.time.get_ticks()
            else:
                sound_start_time = pygame.time.get_ticks()
            sound_started = True

        # Якщо звук стартував — чекаємо його закінчення, потім робимо fade-out (анімація триває)
        if sound_started:
            if ch:
                sound_done = not ch.get_busy()
            else:
                sound_done = (pygame.time.get_ticks() - sound_start_time) >= sound_length_ms

            if sound_done:
                fade_start = pygame.time.get_ticks()
                # підготуємо overlay для fade-out
                out_overlay = pygame.Surface((screen_width, screen_height))
                out_overlay.fill((0, 0, 0))
                while True:
                    for ev in pygame.event.get():
                        if ev.type == QUIT:
                            pygame.quit()
                            raise SystemExit

                    tnow = pygame.time.get_ticks()

                    # продовжуємо анімацію кадрів під час fade-out
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
                    present()
                    clock.tick(60)

                    if progress2 >= 1.0:
                        running_intro = False
                        break

# -------------------- КЛАСИ --------------------
class Button:
    def __init__(self, x, y, w, h, text, image_path=None):
        self.rect = Rect(x, y, w, h)
        self.text = text
        # Підтримка кнопок з зображенням (іконка в центрі)
        self.image = None
        if image_path:
            try:
                img = pygame.image.load(image_path).convert_alpha()
                img = pygame.transform.smoothscale(img, (max(8, w-12), max(8, h-12)))
                self.image = img
            except Exception:
                self.image = None
        self.hovered_last = False
        self.active_last = False  # запам'ятовуємо попередній стан підсвітки/наведення
        self.pressed_until = 0  # ms, время окончания эффекта нажатия
        self.press_duration = 120  # длительность эффекта (ms)

        # плавний перехід кольору
        self.current_color = white
        self.target_color = white
        self.color_smooth = 0.12  # 0..1 - скорость интерполяции (чем больше, тем быстрее)

        # джиттер у спокійному стані
        self.jitter_phase = random.random() * math.pi * 2
        self.jitter_amp = 2.0  # пікселів
        self.jitter_freq = 3.0  # кількість коливань в секунду

    def press(self, duration=None):
        # Запуск візуального ефекту натискання і відтворення кліку
        if duration is None:
            duration = self.press_duration
        self.pressed_until = pygame.time.get_ticks() + duration
        try:
            # відтворюємо заздалегідь завантажений click_sound і повертаємо канал
            if click_sound:
                ch = click_sound.play()
                if ch:
                    ch.set_volume(0.5)
                return ch
        except Exception:
            pass
        return None

    # доданий параметр highlight для підсвітки при навігації клавіатурою
    def draw(self, highlight=False):
        # тепер ігноруємо положення миші — активність визначається лише параметром highlight
        active = bool(highlight)
        now = pygame.time.get_ticks()
        pressed = now < self.pressed_until

        # якщо активна підсвітка — цільовий колір плавно змінюється по RGB-циклу (ефект RGB-підсвітки)
        if active:
            tsec = now / 1000.0
            freq = 1.0  # частота зміни кольорів (Hz) — можна збільшити для швидшої зміни
            # фазовий зсув для R/G/B щоб отримати RGB-циклювання
            r = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + 0.0)))
            g = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + 2.0)))
            b = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + 4.0)))
            self.target_color = (r, g, b)
        else:
            # у спокійному стані повертаємося до білого
            self.target_color = white

        # інтерполюємо поточний колір до цільового (плавний перехід)
        def lerp_color(a, b, t):
            return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
        self.current_color = lerp_color(self.current_color, self.target_color, self.color_smooth)

        # обчислюємо джиттер (лише у спокійному стані, коли не активна і не натиснута)
        jitter_x = jitter_y = 0
        if not active and not pressed:
            tsec = now / 1000.0
            jitter_x = math.sin(tsec * self.jitter_freq + self.jitter_phase) * self.jitter_amp
            # дрібне вертикальне зміщення з меншою амплітудою
            jitter_y = math.sin(tsec * (self.jitter_freq * 1.3) + self.jitter_phase * 0.7) * (self.jitter_amp * 0.6)

        # 3D зсув: тінь зміщена, при натисканні тінь менша і прямокутник зміщений вниз-вправо
        shadow_offset = (6, 6) if not pressed else (2, 2)
        press_offset = (0, 0) if not pressed else (2, 2)

        # відмалювати тінь (беремо до уваги джиттер)
        shadow_rect = self.rect.move(shadow_offset[0] + int(jitter_x), shadow_offset[1] + int(jitter_y))
        pygame.draw.rect(screen, (30, 30, 30), shadow_rect, border_radius=12)

        # основний колір (беремо поточний інтерпольований)
        base_color = self.current_color
        # при натисканні трохи затемнюємо
        if pressed:
            base_color = tuple(max(0, c - 30) for c in base_color)

        # застосовуємо press_offset + джиттер
        draw_rect = self.rect.move(press_offset[0] + int(jitter_x), press_offset[1] + int(jitter_y))
        pygame.draw.rect(screen, base_color, draw_rect, border_radius=10)

        # верхня/ліва підсвітка і нижня/права тінь для об'ємного вигляду
        highlight_color = tuple(min(255, c + 40) for c in base_color)
        pygame.draw.line(screen, highlight_color, (draw_rect.left+4, draw_rect.top+2), (draw_rect.right-4, draw_rect.top+2), 3)
        pygame.draw.line(screen, highlight_color, (draw_rect.left+2, draw_rect.top+4), (draw_rect.left+2, draw_rect.bottom-4), 3)
        dark_color = tuple(max(0, c - 60) for c in base_color)
        pygame.draw.line(screen, dark_color, (draw_rect.left+4, draw_rect.bottom-2), (draw_rect.right-4, draw_rect.bottom-2), 3)
        pygame.draw.line(screen, dark_color, (draw_rect.right-2, draw_rect.top+4), (draw_rect.right-2, draw_rect.bottom-4), 3)

        # Якщо є зображення — показуємо його центрованим на кнопці
        if self.image:
            img_rect = self.image.get_rect(center=draw_rect.center)
            img_rect = img_rect.move(press_offset[0] + int(jitter_x), press_offset[1] + int(jitter_y))
            screen.blit(self.image, img_rect)
        else:
            # текст — зміщуємо при натисканні для відчуття глибини
            text_img = menu_font.render(self.text, True, black)
            text_rect = text_img.get_rect(center=draw_rect.center)
            text_rect = text_rect.move(press_offset[0] + int(jitter_x), press_offset[1] + int(jitter_y))
            screen.blit(text_img, text_rect)

        # Відтворюємо звук тільки при переході в стан active через highlight (клавіатура)
        global hover_channel
        if active and not self.active_last and last_input_was_keyboard:
            try:
                if hover_channel is None or not hover_channel.get_busy():
                    hover_channel = hover_sound.play()
                    if hover_channel:
                        hover_channel.set_volume(0.5)
            except Exception:
                pass

        # оновлюємо стани для наступного кадру
        self.active_last = active

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class Paddle:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 20, 100)
        self.original_height = self.rect.height
        self.speed = 5
        self.reaction_time = 0
        self.large_until = None  # час завершення збільшення ракетки (ms)

    def move(self, up_key, down_key):
        keys = pygame.key.get_pressed()
        # обмеження по верхньому/нижньому бордеру
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
        # якщо час збільшеної ракетки минув — повернути оригінальний розмір
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
                    # запасний варіант — просте інвертування
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

# Параметри режиму вікна і підтвердження змін у налаштуваннях
window_modes = ['windowed', 'bordered', 'fullscreen']
current_window_mode = 'windowed'
settings_option_index = 0  # 0 = volume, 1 = window mode
settings_window_mode_index = 1  # default -> 'bordered'
preview_active = False
prev_window_mode = None
prev_window_size = (window_width, window_height)

def apply_window_mode(mode, preview=False):
    """Apply window mode. If preview=True - store previous state so it can be reverted."""
    global real_screen, window_width, window_height, current_window_mode, preview_active, prev_window_mode, prev_window_size
    try:
        if preview and not preview_active:
            prev_window_mode = current_window_mode
            prev_window_size = (window_width, window_height)
            preview_active = True

        if mode == 'fullscreen':
            info = pygame.display.Info()
            window_width, window_height = info.current_w, info.current_h
            flags = pygame.FULLSCREEN
        elif mode == 'windowed':
            window_width, window_height = screen_width, screen_height
            flags = pygame.RESIZABLE
        else:  # 'bordered' - normal window with frame
            window_width, window_height = screen_width, screen_height
            flags = 0

        real_screen = pygame.display.set_mode((window_width, window_height), flags)

        if not preview:
            current_window_mode = mode
            preview_active = False
            try:
                save_settings()
            except Exception:
                pass
    except Exception:
        pass

def present():
    """Scale virtual `screen` to the real window and update display."""
    global real_screen, window_width, window_height
    try:
        # preserve aspect ratio: scale logical screen to fit into real window
        sw, sh = screen_width, screen_height
        ww, wh = window_width, window_height
        scale_f = min(float(ww) / sw, float(wh) / sh)

        # prefer integer scaling when close to integer multiples (keeps pixels crisper)
        use_scale = scale_f
        if scale_f >= 2.0:
            int_scale = int(scale_f)
            if abs(scale_f - int_scale) < 0.18:
                use_scale = float(int_scale)

        scaled_w = max(1, int(round(sw * use_scale)))
        scaled_h = max(1, int(round(sh * use_scale)))

        # choose scaling method: nearest-neighbor for integer multiples, smooth otherwise
        if abs(use_scale - round(use_scale)) < 1e-6 and use_scale >= 1.0:
            scaled_surf = pygame.transform.scale(screen, (scaled_w, scaled_h))
        else:
            try:
                scaled_surf = pygame.transform.smoothscale(screen, (scaled_w, scaled_h))
            except Exception:
                scaled_surf = pygame.transform.scale(screen, (scaled_w, scaled_h))

        # center the scaled surface and letterbox (black bars)
        real_screen.fill((0, 0, 0))
        x = (ww - scaled_w) // 2
        y = (wh - scaled_h) // 2
        real_screen.blit(scaled_surf, (x, y))
        pygame.display.update()
    except Exception:
        try:
            pygame.display.update()
        except Exception:
            pass

# ---- Settings persistence ----
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')

def load_settings():
    global settings_volume, settings_window_mode_index, current_window_mode, preview_active, prev_window_mode, prev_window_size
    try:
        if os.path.isfile(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
            settings_volume = float(data.get('volume', settings_volume))
            saved_mode = data.get('window_mode', current_window_mode)
            if saved_mode in window_modes:
                settings_window_mode_index = window_modes.index(saved_mode)
                current_window_mode = saved_mode
                # apply saved window mode as actual (not preview)
                try:
                    apply_window_mode(current_window_mode, preview=False)
                except Exception:
                    pass
            # apply volume to mixer if available
            if sound_enabled:
                try:
                    pygame.mixer.music.set_volume(settings_volume)
                except Exception:
                    pass
    except Exception:
        pass

def save_settings():
    try:
        data = {
            'volume': float(settings_volume),
            'window_mode': str(current_window_mode)
        }
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass


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

# load persisted settings (volume, window mode) before starting
load_settings()

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
                    try:
                        save_settings()
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
                try:
                    save_settings()
                except Exception:
                    pass

        # Якщо чекаємо натискання клавіші після гола — обробляємо спеціально:
        if waiting_for_key and event.type == KEYDOWN:
            # продолжение игры — только по пробелу
            if event.key == K_SPACE:
                waiting_for_key = False
                # ховаємо підсвітку кнопок
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
                        present()
                        fade_while_channel_busy(ch)
                        # Back -> в главное меню
                        state = "menu"
                        player_score = cpu_score = 0
                        play_music(music_menu)
                        waiting_for_key = False
                    else:
                        ch = btn_exit_pause.press()
                        present()
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

            # Якщо ми в меню налаштувань — обробляємо клавіші тут (ESC — назад, стрілки — гучність)
            if state == "settings":
                # ESC: якщо є активне прев'ю — скасовуємо його, інакше повертаємось в меню
                if event.key == K_ESCAPE:
                    if preview_active:
                        # відкотити прев'ю
                        try:
                            if prev_window_mode:
                                apply_window_mode(prev_window_mode, preview=False)
                                settings_window_mode_index = window_modes.index(prev_window_mode) if prev_window_mode in window_modes else settings_window_mode_index
                        except Exception:
                            pass
                        preview_active = False
                        prev_window_mode = None
                        prev_window_size = (window_width, window_height)
                        last_input_was_keyboard = True
                        continue
                    state = "menu"
                    last_input_was_keyboard = True
                    continue

                # Навігація між опціями у налаштуваннях
                if event.key in (K_UP, K_w):
                    settings_option_index = max(0, settings_option_index - 1)
                    continue
                if event.key in (K_DOWN, K_s):
                    settings_option_index = min(1, settings_option_index + 1)
                    continue

                # Ліво/право змінює значення поточної опції
                if event.key in (K_LEFT, K_a):
                    if settings_option_index == 0:
                        settings_volume = max(0.0, settings_volume - 0.05)
                        if sound_enabled:
                            try:
                                pygame.mixer.music.set_volume(settings_volume)
                            except Exception:
                                pass
                        try:
                            save_settings()
                        except Exception:
                            pass
                    else:
                        # циклічне перемикання режиму вікна вліво (прев'ю)
                        settings_window_mode_index = (settings_window_mode_index - 1) % len(window_modes)
                        apply_window_mode(window_modes[settings_window_mode_index], preview=True)
                    continue
                if event.key in (K_RIGHT, K_d):
                    if settings_option_index == 0:
                        settings_volume = min(1.0, settings_volume + 0.05)
                        if sound_enabled:
                            try:
                                pygame.mixer.music.set_volume(settings_volume)
                            except Exception:
                                pass
                    try:
                        save_settings()
                    except Exception:
                        pass
                    else:
                        # циклічне перемикання режиму вікна вправо (прев'ю)
                        settings_window_mode_index = (settings_window_mode_index + 1) % len(window_modes)
                        apply_window_mode(window_modes[settings_window_mode_index], preview=True)
                    continue

                # ENTER: підтвердження вибраної опції (в основному — для підтвердження режиму вікна)
                if event.key in (K_RETURN, K_KP_ENTER):
                    if settings_option_index == 1 and preview_active:
                        # зафіксувати вибір вікна
                        apply_window_mode(window_modes[settings_window_mode_index], preview=False)
                        preview_active = False
                        prev_window_mode = None
                        prev_window_size = (window_width, window_height)
                        last_input_was_keyboard = True
                        continue
                    # інші підтвердження (напр., volume) не потребують окремого прийняття
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
                        present()
                        pygame.time.wait(120)
                        # гарантируем режим AI при входе в выбор сложности
                        mode = "ai"
                        state = "difficulty"
                    elif menu_index == 1:
                        btn_pvp.press()
                        present()
                        pygame.time.wait(120)
                        mode = "pvp"
                        # создаём мяч для PVP со стандартной скоростью PVP (используем среднюю)
                        pong = Ball(screen_width // 2, screen_height // 2, difficulty_ball_speed(None))
                        state = "game"
                        play_music(music_pvp)
                    elif menu_index == 2:
                        btn_exit.press()
                        present()
                        pygame.time.wait(120)
                        running = False
                    elif menu_index == 3:
                        # открыть меню настроек
                        btn_settings.press()
                        present()
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
                        present()
                        fade_while_channel_busy(ch)
                        # явно переключаем режим на AI при старте игры из меню сложности
                        mode = "ai"
                        difficulty = "easy"
                        play_music(music_easy)
                        state = "game"
                    elif diff_index == 1:
                        ch = btn_med.press()
                        present()
                        fade_while_channel_busy(ch)
                        mode = "ai"
                        difficulty = "medium"
                        play_music(music_medium)
                        state = "game"
                    elif diff_index == 2:
                        ch = btn_hard.press()
                        present()
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
                        present()
                        fade_while_channel_busy(ch)
                        state = "menu"
                        if click_sound:
                            try:
                                click_sound.play().set_volume(0.5)
                            except Exception:
                                pass

    # -------------------- МЕНЮ --------------------
    if state == "menu":
        # відмалювання анімованого фону для головного меню (якщо кадри завантажені)
        if backmain_frames:
            now = pygame.time.get_ticks()
            if now - backmain_last_frame_time >= backmain_frame_interval:
                backmain_frame_index = (backmain_frame_index + 1) % len(backmain_frames)
                backmain_last_frame_time = now
            screen.blit(backmain_frames[backmain_frame_index], (0, 0))
        else:
            # запасний варіант — звичайний фон
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
        # підсвічуємо вибрану кнопку
        btn_ai.draw(highlight=(menu_index==0))
        btn_pvp.draw(highlight=(menu_index==1))
        btn_exit.draw(highlight=(menu_index==2))
        # settings cog in menu (styled like others)
        btn_settings.draw(highlight=(menu_index==3))

    # -------------------- ВЫБОР СЛОЖНОСТИ --------------------
    elif state == "difficulty":
        # відмалювання анімованого фону для меню вибору складності (якщо кадри завантажені)
        if backdiff_frames:
            now = pygame.time.get_ticks()
            if now - backdiff_last_frame_time >= backdiff_frame_interval:
                backdiff_frame_index = (backdiff_frame_index + 1) % len(backdiff_frames)
                backdiff_last_frame_time = now
            screen.blit(backdiff_frames[backdiff_frame_index], (0, 0))
        else:
            # запасний варіант — звичайний фон
            screen.fill(background)

        menu_timer += 1
        pulse_offset = math.sin(menu_timer * 0.05) * menu_pulse_amplitude
        swing_angle = math.sin(menu_timer * 0.05) * menu_swing_angle
        # По-кожній літері RGB-підсвітка заголовка "Choose Your Way"
        title = "Choose Your Way"
        now = pygame.time.get_ticks()
        tsec = now / 1000.0
        # підготуємо поверхні для кожної літери з індивідуальним кольором і чорним контуром
        letter_surfs = []
        total_w = 0
        max_h = 0
        for i, ch in enumerate(title):
            # фазовий зсув по індексу для гарного градієнта
            phase = i * 0.25
            freq = 1.0
            r = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + phase + 0.0)))
            g = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + phase + 2.0)))
            b = int(100 + 155 * (0.5 + 0.5 * math.sin(2 * math.pi * freq * tsec + phase + 4.0)))
            col = (r, g, b)
            # рендеримо літеру кольором і чорний контур (кілька зміщень)
            color_surf = font_big.render(ch, True, col).convert_alpha()
            bw, bh = color_surf.get_size()
            # створюємо поверхню з запасом під контур
            surf = pygame.Surface((bw + 4, bh + 4), pygame.SRCALPHA)
            black_surf = font_big.render(ch, True, black).convert_alpha()
            # зміщення для контуру (товщина обвідки)
            offsets = [(-2,0),(2,0),(0,-2),(0,2),(-1,-1),(1,-1),(-1,1),(1,1)]
            for ox, oy in offsets:
                surf.blit(black_surf, (2 + ox, 2 + oy))
            # центральна кольорова літера
            surf.blit(color_surf, (2, 2))
            letter_surfs.append(surf)
            total_w += surf.get_width()
            max_h = max(max_h, surf.get_height())
        # зберемо рядок у прозору поверхню
        text_surf = pygame.Surface((total_w, max_h), pygame.SRCALPHA)
        x = 0
        for surf in letter_surfs:
            text_surf.blit(surf, (x, 0))
            x += surf.get_width()
        # поворот і центрування як раніше
        rotated_img = pygame.transform.rotate(text_surf, swing_angle)
        rotated_rect = rotated_img.get_rect(center=(300, 120 + pulse_offset))
        screen.blit(rotated_img, rotated_rect)
        # підсвічуємо вибрану кнопку складності
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

        # Текст і інструкція (підсвітка букв для активної опції)
        # Music Volume (letter-highlight when focused)
        mv = "Music Volume"
        mv_x = screen_width//2
        mv_y = slider_rect.top - 30
        if settings_option_index == 0:
            now = pygame.time.get_ticks() / 1000.0
            x_offset = 0
            # render per-letter with subtle RGB pulse
            total_w = sum(font.render(ch, True, white).get_width() for ch in mv)
            start_x = mv_x - total_w//2
            cx = start_x
            for i, ch in enumerate(mv):
                phase = i * 0.2
                r = int(180 + 60 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.8 * now + phase)))
                g = int(180 + 60 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.8 * now + phase + 2.0)))
                b = int(200 + 55 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.8 * now + phase + 4.0)))
                col = (r, g, b)
                ch_surf = font.render(ch, True, col)
                screen.blit(ch_surf, (cx, mv_y - ch_surf.get_height()//2))
                cx += ch_surf.get_width()
        else:
            draw_text("Music Volume", font, (200,200,200), screen_width//2, slider_rect.top - 30, center=True)

        # Window Mode (redesigned block with arrows, white style)
        # Header with per-letter highlight when focused
        header = "Window Mode"
        hdr_x = screen_width//2
        hdr_y = slider_rect.bottom + 40
        if settings_option_index == 1:
            now = pygame.time.get_ticks() / 1000.0
            total_w = sum(font.render(ch, True, white).get_width() for ch in header)
            start_x = hdr_x - total_w//2
            cx = start_x
            for i, ch in enumerate(header):
                phase = i * 0.18
                r = int(160 + 95 * (0.5 + 0.5 * math.sin(2 * math.pi * 1.0 * now + phase)))
                g = int(160 + 95 * (0.5 + 0.5 * math.sin(2 * math.pi * 1.0 * now + phase + 2.0)))
                b = int(160 + 95 * (0.5 + 0.5 * math.sin(2 * math.pi * 1.0 * now + phase + 4.0)))
                col = (min(255,r), min(255,g), min(255,b))
                ch_surf = font.render(ch, True, col)
                screen.blit(ch_surf, (cx, hdr_y - ch_surf.get_height()//2))
                cx += ch_surf.get_width()
        else:
            draw_text("Window Mode", font, (100,100,100), screen_width//2, hdr_y, center=True)

        # block dimensions (scale with screen width)
        block_w = min(520, int(screen_width * 0.75))
        block_h = 86
        block_x = screen_width//2 - block_w//2
        block_y = slider_rect.bottom + 60
        block_rect = pygame.Rect(block_x, block_y, block_w, block_h)

        # block background: near-white (slightly off-white)
        pygame.draw.rect(screen, (235,235,235), block_rect, border_radius=14)

        # subtle outer glow when selected
        if settings_option_index == 1:
            glow_rect = block_rect.inflate(18, 12)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            glow_surf.fill((220, 240, 255, 28))
            screen.blit(glow_surf, glow_rect.topleft)

        # draw left/right triangle arrows outside the block
        tri_w = 36
        tri_h = 34
        cy = block_rect.centery
        # left triangle (points left) placed left of block
        left_tip_x = block_rect.left - 16
        left_tri = [
            (left_tip_x, cy),
            (left_tip_x + tri_w, cy - tri_h//2),
            (left_tip_x + tri_w, cy + tri_h//2),
        ]
        # right triangle (points right) placed right of block
        right_tip_x = block_rect.right + 16
        right_tri = [
            (right_tip_x, cy),
            (right_tip_x - tri_w, cy - tri_h//2),
            (right_tip_x - tri_w, cy + tri_h//2),
        ]
        tri_color = (20,20,20) if settings_option_index==1 else (90,110,130)
        pygame.draw.polygon(screen, tri_color, left_tri)
        pygame.draw.polygon(screen, tri_color, right_tri)

        # center text: current mode (per-letter subtle highlight when focused)
        mode_name = window_modes[settings_window_mode_index].capitalize()
        text_x = block_rect.centerx
        text_y = block_rect.centery
        if settings_option_index == 1:
            now = pygame.time.get_ticks() / 1000.0
            total_w = sum(font.render(ch, True, (30,30,30)).get_width() for ch in mode_name)
            start_x = text_x - total_w//2
            cx = start_x
            for i, ch in enumerate(mode_name):
                phase = i * 0.15
                r = int(40 + 200 * (0.5 + 0.5 * math.sin(2 * math.pi * 1.2 * now + phase)))
                g = int(40 + 200 * (0.5 + 0.5 * math.sin(2 * math.pi * 1.2 * now + phase + 2.0)))
                b = int(40 + 200 * (0.5 + 0.5 * math.sin(2 * math.pi * 1.2 * now + phase + 4.0)))
                col = (min(255,r), min(255,g), min(255,b))
                ch_surf = font.render(ch, True, col)
                screen.blit(ch_surf, (cx, text_y - ch_surf.get_height()//2))
                cx += ch_surf.get_width()
        else:
            draw_text(mode_name, font, (40,40,40), text_x, text_y, center=True)

        # preview hint
        if preview_active:
            draw_text("Preview active — Press ENTER to confirm or ESC to cancel", font, (80,80,80), screen_width//2, block_rect.bottom + 26, center=True)

        # Рисуем кнопку шестерёнки (чтобы пользователь видел куда нажимал)
        # btn_settings.draw()

        # Нижній інструкційний текст — завжди внизу екрану
        draw_text("Press ESC to return", font, (150,150,150), screen_width//2, screen_height - 28, center=True)

    # -------------------- ИГРА --------------------
    elif state == "game":
        draw_board()
        if mode == "pvp":
            draw_text(f"P1: {player_score}   P2: {cpu_score}", font, white, 200, 10)
        else:  # против ИИ
            draw_text(f"P1: {player_score}   AI: {cpu_score}", font, white, 200, 10)


        # Якщо чекаємо натискання клавіші, просто виводимо текст
        if waiting_for_key:
            draw_text("Press SPACE to continue...", font, white, screen_width//2, screen_height//2, center=True)
            # малюємо кнопки Back і Exit під текстом (підсвітка за pause_index)
            btn_back_pause.draw(highlight=(pause_index==0))
            btn_exit_pause.draw(highlight=(pause_index==1))
        else:
            # Управління гравцями
            if mode == "pvp":
                player_paddle.move(K_w, K_s)
                cpu_paddle.move(K_UP, K_DOWN)
            else:
                player_paddle.move(K_w, K_s)
                cpu_paddle.ai(pong, difficulty)

            # оновлюємо стани ракеток (в т.ч. таймери збільшення)
            player_paddle.update()
            cpu_paddle.update()

            # Малюємо об'єкти
            player_paddle.draw()
            cpu_paddle.draw()
            pong.draw()

            # Бустери
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

            # Рух м'яча
            winner = pong.move([(player_paddle, "player"), (cpu_paddle, "cpu")], boosters, walls)
            if winner != 0:
                waiting_for_key = True  # ждём нажатия клавиши перед продолжением
                # выравниваем по центру игровой области
                cpu_paddle.rect.centery = center_y
                player_paddle.rect.centery = center_y
                pong = Ball(screen_width // 2, center_y, 5)
                # Сброс мяча и ракеток
                pygame.time.wait(100)
                present()
                if winner == 1:
                    cpu_score += 1
                    try:
                        if goal_sound:
                            goal_sound.play()
                    except Exception:
                        pass
                    draw_text("YOU LOST!", font_big, white, 300, 250, center=True)
                else:
                    player_score += 1
                    try:
                        if lose_sound:
                            lose_sound.play()
                    except Exception:
                        pass
                    draw_text("YOU SCORED!", font_big, white, 300, 250, center=True)
                present()
                pygame.time.wait(2000)

                # Сброс мяча и ракеток
                # создаём новый мяч: если режим AI — скорость по выбранной сложности, иначе средняя
                new_speed = difficulty_ball_speed(difficulty) if mode == "ai" and difficulty else difficulty_ball_speed(None)
                pong = Ball(screen_width // 2, center_y, new_speed)
                player_paddle.rect.centery = center_y
                cpu_paddle.rect.centery = center_y

                waiting_for_key = True  # ждём нажатия клавиши перед продолжением


    # Накладання повідомлення про відсутність гарнітури (внизу зліва)
    if headset_warning and headset_warning_start:
        try:
            now = pygame.time.get_ticks()
            elapsed = now - headset_warning_start
            # якщо ще триває період показу — повна непрозорість, таймер лінії зменшується
            if elapsed < HEADSET_WARNING_DISPLAY:
                display_progress = max(0.0, min(1.0, float(elapsed) / HEADSET_WARNING_DISPLAY))
                alpha = 255
                timer_progress = 1.0 - display_progress

                text = "You have no headset for sound"
                txt_surf = font.render(text, True, (255, 255, 255))
                pad_x = 12
                pad_y = 10
                box_w = txt_surf.get_width() + pad_x * 2
                box_h = txt_surf.get_height() + pad_y * 2
                bx = 10
                by = screen_height - box_h - 10

                box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
                box_surf.fill((20, 20, 20, alpha))
                # невелика внутрішня тінь (темніша прямокутна вставка)
                inner = pygame.Surface((box_w - 4, box_h - 4), pygame.SRCALPHA)
                inner.fill((30, 30, 30, max(0, alpha - 30)))
                box_surf.blit(inner, (2, 2))

                box_surf.blit(txt_surf, (pad_x, pad_y))

                # лінія-таймер (стягується справа наліво під час показу)
                full_bar_w = box_w - pad_x * 2
                bar_h = 6
                curr_w = int(full_bar_w * timer_progress)
                if curr_w < 1:
                    curr_w = 0
                if curr_w > 0:
                    bar_surf = pygame.Surface((curr_w, bar_h), pygame.SRCALPHA)
                    # робимо смужку напівпрозорою і прив'язуємо до alpha
                    bar_surf.fill((255, 255, 255, max(30, int(alpha * 0.9))))
                    box_surf.blit(bar_surf, (pad_x, box_h - pad_y - bar_h))

                # тонка тінь під лінією
                shadow = pygame.Surface((full_bar_w, 2), pygame.SRCALPHA)
                shadow.fill((0, 0, 0, max(20, int(alpha * 0.6))))
                # відмалювати блок і тінь на екрані
                screen.blit(box_surf, (bx, by))
                screen.blit(shadow, (bx + pad_x, by + box_h - pad_y + 6))
            # якщо період показу завершився — запускаємо затемнення на окремому інтервалі
            elif elapsed < HEADSET_WARNING_DISPLAY + HEADSET_WARNING_FADE:
                fade_elapsed = elapsed - HEADSET_WARNING_DISPLAY
                fade_progress = max(0.0, min(1.0, float(fade_elapsed) / HEADSET_WARNING_FADE))
                alpha = int(255 * (1.0 - fade_progress))

                text = "You have no headset for sound"
                txt_surf = font.render(text, True, (255, 255, 255))
                pad_x = 12
                pad_y = 10
                box_w = txt_surf.get_width() + pad_x * 2
                box_h = txt_surf.get_height() + pad_y * 2
                bx = 10
                by = screen_height - box_h - 10

                box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
                box_surf.fill((20, 20, 20, alpha))
                inner = pygame.Surface((box_w - 4, box_h - 4), pygame.SRCALPHA)
                inner.fill((30, 30, 30, max(0, alpha - 30)))
                box_surf.blit(inner, (2, 2))
                box_surf.blit(txt_surf, (pad_x, pad_y))

                # під час затемнення лінія вже закінчилась — не малюємо її
                screen.blit(box_surf, (bx, by))
            else:
                headset_warning = False
        except Exception:
            headset_warning = False

    present()

try:
    save_settings()
except Exception:
    pass

pygame.quit()