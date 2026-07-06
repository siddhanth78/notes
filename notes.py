import pygame
import os
from pathlib import Path
import sys
import tempfile
# from suggest import Tree

pygame.init()

all_monitors = pygame.display.get_desktop_sizes()

WIDTH, HEIGHT = all_monitors[0][0], all_monitors[0][1] - 100

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.key.set_repeat(200, 50)

cw, ch = 12, 20
offset_ = 5

fonts = {
    16: pygame.font.SysFont("firacodemedium", 16),
    20: pygame.font.SysFont("firacodemedium", 20),
    24: pygame.font.SysFont("firacodemedium", 24)
}

font = fonts[ch]
dialog_font = pygame.font.SysFont("firacodemedium", 16)

window_x = [0, (WIDTH//cw) - 1]
window_y = [0, (HEIGHT//(ch+offset_)) - 1]

filepath = None

if len(sys.argv) > 1:
    filepath = Path(sys.argv[1])
    if os.path.exists(filepath):
        with open(filepath, "r") as file:
            text = file.readlines()
    else:
        print("File doesn't exist")
        quit()
else:
    filepath = Path("~/Notes/new.txt").expanduser()
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as file:
        file.write("")
    text = [""]

default_save_dir = "~/Notes/"

w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
all_text = '\n'.join(w_text)

text_color = (255,255,255)
cursor_color = (128,128,128)

text_surface = font.render(all_text, False, text_color)
cursor = [0,0]

clock = pygame.time.Clock()

running = True

fstr = str(filepath)
if len(fstr) > 20:
    caption = fstr[:10] + "..." + fstr[10:]
else:
    caption = fstr

pygame.display.set_caption(caption)

unsaved_exit = False

selection = False

def unsavedDialog(surface_):
    rect_ = pygame.Rect(0, 0, 300, 100)
    rect_.center = screen.get_rect().center
    pygame.draw.rect(surface_, (0, 0, 0), rect_)
    question = "Quit without saving? (y/n)"
    texts = dialog_font.render(question, False, (128, 128, 0), bgcolor=(0, 0, 0))
    surface_.blit(texts, (20,40))
    return surface_

def render_window():
    w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
    all_text = '\n'.join(w_text)
    text_surface = font.render(all_text, False, text_color)
    return text_surface

def slide_x(n):
    window_x[0] += n
    window_x[1] += n

def slide_y(n):
    window_y[0] += n
    window_y[1] += n

def zoom(step):
    global cw, ch, offset_, font
    if (16 < ch <= 24 and step == -1) or (16 <= ch < 24 and step == 1):
        ch += step*4
        if ch == 24:
            cw, ch = 15, 24
            offset_ = 6
        elif ch == 20:
            cw, ch = 12, 20
            offset_ = 5
        else:
            cw, ch = 10, 16
            offset_ = 4
        font = fonts[ch]
        set_window()

def set_window():
    cols = (WIDTH//cw) - 1
    rows = (HEIGHT//(ch+offset_)) - 1

    window_x[0] = max(cursor[0] - cols, 0)
    window_x[1] = window_x[0] + cols + 1

    window_y[0] = max(cursor[1] - rows, 0)
    window_y[1] = window_y[0] + rows + 1

dialog_surface = pygame.Surface((300,100))
unsaved_dialog = unsavedDialog(dialog_surface)

while running:
    screen.fill((32,32,32))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                captioncheck = pygame.display.get_caption()[0][-1]
                if captioncheck == "*":
                    unsaved_exit = True
                else:
                    running = False
            elif event.key == pygame.K_y and unsaved_exit == True:
                running = False
            elif event.key == pygame.K_n and unsaved_exit == True:
                unsaved_exit = False
            elif event.key == pygame.K_LEFT and unsaved_exit == False:
                cx = cursor[0]
                if cx == window_x[0]+3 and cx > 0:
                    if window_x[0] > 0:
                        slide_x(-1)
                        w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
                        all_text = '\n'.join(w_text)
                        text_surface = font.render(all_text, False, text_color)
                cursor[0] = max(0, cx-1) 
            elif event.key == pygame.K_RIGHT and unsaved_exit == False:
                cx = cursor[0]
                if cx >= window_x[1]-3 and cx > 0:
                    if window_x[1] < len(text[cursor[1]]):
                        slide_x(1)
                        w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
                        all_text = '\n'.join(w_text)
                        text_surface = font.render(all_text, False, text_color)
                cursor[0] = min(len(text[cursor[1]]), cx+1)
            elif event.key == pygame.K_UP and unsaved_exit == False:
                cy = cursor[1]
                cursor[1] = max(0, cy-1)
                cursor[0] = min(len(text[cursor[1]]), cursor[0])
                wflag = 0
                if cy == window_y[0]+3 and cy > 0:
                    if window_y[0] > 0:
                        slide_y(-1)
                        wflag = 1
                if len(text[cursor[1]]) < len(text[cy]):
                    window_x[0] = max(len(text[cursor[1]]) - ((WIDTH//cw)-1), 0)
                    window_x[1] = max(len(text[cursor[1]]), (WIDTH//cw)-1)
                    wflag = 1
                if wflag == 1:
                    text_surface = render_window()
            elif event.key == pygame.K_DOWN and unsaved_exit == False:
                cy = cursor[1]
                cursor[1] = min(len(text)-1, cy+1)
                cursor[0] = min(len(text[cursor[1]]), cursor[0])
                wflag = 0
                if cy == window_y[1]-3 and cy > 0:
                    if window_y[1] < len(text):
                        slide_y(1)
                        wflag = 1
                if len(text[cursor[1]]) < len(text[cy]):
                    window_x[0] = max(len(text[cursor[1]]) - ((WIDTH//cw)-1), 0)
                    window_x[1] = max(len(text[cursor[1]]), (WIDTH//cw)-1)
                    wflag = 1
                if wflag == 1:
                    text_surface = render_window()
            elif event.key == pygame.K_EQUALS and (event.mod & pygame.KMOD_CTRL) and (event.mod & pygame.KMOD_SHIFT) and unsaved_exit == False:
                zoom(1)
                text_surface = render_window()
            elif event.key == pygame.K_MINUS and (event.mod & pygame.KMOD_CTRL) and (event.mod & pygame.KMOD_SHIFT) and unsaved_exit == False:
                zoom(-1)
                text_surface = render_window()
            elif event.key == pygame.K_BACKSPACE and unsaved_exit == False:
                pygame.display.set_caption(caption + "*")
                if cursor[0] > 0 and text[cursor[1]]:
                    text[cursor[1]] = text[cursor[1]][:cursor[0]-1] + text[cursor[1]][cursor[0]:]
                    if cursor[0] <= window_x[0]+3:
                        if window_x[0] > 0:
                            slide_x(-1)
                    cursor[0] -= 1
                    cursor[0] = max(0, cursor[0])
                    text_surface = render_window()
                elif cursor[0] == 0 and cursor[1] == window_y[0]+3 and cursor[1] > 0:
                    if window_y[0] > 0:
                        slide_y(-1)
                    cursor[0] = len(text[cursor[1]-1])
                    popped = text.pop(cursor[1])
                    text[cursor[1]-1] += popped
                    if cursor[0] > (WIDTH//cw)-1:
                        slide_x(cursor[0] - ((WIDTH//cw)-1))
                    cursor[1] -= 1
                    text_surface = render_window()
                elif cursor[0] == 0 and cursor[1]>0:
                    cursor[0] = len(text[cursor[1]-1])
                    popped = text.pop(cursor[1])
                    text[cursor[1]-1] += popped
                    if cursor[0] > (WIDTH//cw)-1:
                        slide_x(cursor[0] - ((WIDTH//cw)-1))
                    cursor[1] -= 1
                    text_surface = render_window()
            elif event.key == pygame.K_TAB and unsaved_exit == False:
                pygame.display.set_caption(caption + "*")
                text[cursor[1]] = text[cursor[1]][:cursor[0]] + " "*4 + text[cursor[1]][cursor[0]:]
                if cursor[0] > window_x[1]-4:
                    w1 = window_x[1]
                    slide_x(4-(w1 - cursor[0]))
                cursor[0] += 4
                text_surface = render_window()
            elif event.key == pygame.K_SPACE and unsaved_exit == False:
                pygame.display.set_caption(caption + "*")
                text[cursor[1]] = text[cursor[1]][:cursor[0]] + " " + text[cursor[1]][cursor[0]:]
                if cursor[0] == window_x[1]:
                    slide_x(1)
                cursor[0] += 1
                text_surface = render_window()
            elif event.key == pygame.K_RETURN and unsaved_exit == False:
                pygame.display.set_caption(caption + "*")
                text.insert(cursor[1]+1, "")
                text[cursor[1]+1] = text[cursor[1]][cursor[0]:]
                text[cursor[1]] = text[cursor[1]][:cursor[0]]
                cursor[1] += 1
                cursor[0] = 0
                if cursor[1] == window_y[1]:
                    slide_y(1)
                window_x[0] = 0
                window_x[1] = (WIDTH//cw)-1
                text_surface = render_window()
            elif event.key == pygame.K_s and (event.mod & pygame.KMOD_CTRL) and unsaved_exit == False:
                fd, temp_path = tempfile.mkstemp(dir=filepath.parent, suffix=".tmp")
                try:
                    with os.fdopen(fd, 'w') as f:
                        f.write("\n".join(text))
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(temp_path, filepath)
                    pygame.display.set_caption(caption)
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            elif event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL) and unsaved_exit == False:
                selection = not selection
            elif event.mod & pygame.KMOD_CTRL:
                pass
            else:
                if unsaved_exit == False:
                    new_text = text[cursor[1]][:cursor[0]] + event.unicode + text[cursor[1]][cursor[0]:]
                    if len(new_text) != len(text[cursor[1]]):
                        pygame.display.set_caption(caption + "*")
                        text[cursor[1]] = new_text
                        if cursor[0] == window_x[1]:
                            slide_x(1)
                        cursor[0] += 1
                        text_surface = render_window()

    pygame.draw.rect(screen, (64, 64, 64), (0, (ch+offset_)*(cursor[1]-window_y[0]), WIDTH, ch))
    pygame.draw.rect(screen, cursor_color, (cw*(cursor[0]-window_x[0]), (ch+offset_)*(cursor[1]-window_y[0]), cw, ch), 2)
    screen.blit(text_surface, (0,0))

    if unsaved_exit == True:
        screen.blit(unsaved_dialog, ((WIDTH//2)-150, (HEIGHT//2)-50))

    pygame.display.update()
    clock.tick(60)

pygame.quit()
