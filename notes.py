import pygame
import os
from pathlib import Path
import sys
import tempfile
import pyperclip
import curses
import re
import mmap
import bisect
import subprocess
import json
import shutil

pygame.init()

RG_PATH = shutil.which("rg")
MAX_FILE_SIZE = 500 * 1024 * 1024

all_monitors = pygame.display.get_desktop_sizes()

WIDTH, HEIGHT = all_monitors[0][0], all_monitors[0][1] - 150

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

default_save_dir = "~/Notes/"

SUPPORTED_EXTENSIONS = [
    ".txt", ".md", ".py", ".json", ".csv",
    ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
    ".c", ".cpp", ".h", ".hpp", ".java", ".go", ".rs", ".rb", ".php",
    ".sh", ".bash", ".zsh", ".sql", ".lua", ".pl", ".swift", ".kt",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".xml",
    ".rst", ".tex", ".log", ".tsv", ".gitignore", ".editorconfig"
]

def open_note_explorer(base_dir):
    base_dir = Path(base_dir).expanduser()
    base_dir.mkdir(parents=True, exist_ok=True)
    current_dir = base_dir

    def run(stdscr):
        nonlocal current_dir
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)    # directories
        curses.init_pair(2, curses.COLOR_WHITE, -1)   # files
        curses.init_pair(3, curses.COLOR_GREEN, -1)   # create actions
        curses.init_pair(4, curses.COLOR_YELLOW, -1)  # rename/delete current dir

        selected = 0
        scroll = 0
        while True:
            curses.curs_set(0)
            entries = sorted(os.listdir(current_dir))
            items = [("+ Create new note here", None, "new"), ("+ Create new dir here", None, "newdir")]

            if current_dir != base_dir:
                items.append(("+ Rename this directory", None, "renamedir"))
                if not os.listdir(current_dir):
                    items.append(("+ Delete this directory", None, "deletedir"))

            for e in entries:
                full = current_dir / e
                if full.is_dir():
                    items.append((e + "/", full, "dir"))
                elif os.path.splitext(e)[1] in SUPPORTED_EXTENSIONS:
                    items.append((e, full, "file"))

            if current_dir != base_dir:
                items.insert(0, ("..", current_dir.parent, "dir"))

            h, w = stdscr.getmaxyx()
            list_top = 3
            list_bottom = h - 2
            visible_rows = max(1, list_bottom - list_top)

            if selected < scroll:
                scroll = selected
            elif selected >= scroll + visible_rows:
                scroll = selected - visible_rows + 1
            scroll = max(0, min(scroll, max(0, len(items) - visible_rows)))

            stdscr.clear()
            stdscr.addstr(0, 0, "Notes", curses.A_BOLD)
            stdscr.addstr(1, 0, f"Dir: {current_dir}"[:w-1])

            visible_items = items[scroll:scroll + visible_rows]
            for row, (name, _, kind) in enumerate(visible_items):
                idx = scroll + row
                prefix = "> " if idx == selected else "  "
                if kind in ("new", "newdir"):
                    color = curses.color_pair(3)
                elif kind in ("renamedir", "deletedir"):
                    color = curses.color_pair(4)
                elif kind == "dir":
                    color = curses.color_pair(1)
                else:
                    color = curses.color_pair(2)
                attr = curses.A_REVERSE if idx == selected else color
                stdscr.addstr(list_top + row, 0, (prefix + name)[:w-1], attr)

            footer = f"↑/↓ move  Enter select  Esc cancel  ({selected+1}/{len(items)})"
            stdscr.addstr(h - 1, 0, footer[:w-1], curses.A_DIM)
            stdscr.refresh()

            key = stdscr.getch()
            if key == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif key == curses.KEY_DOWN:
                selected = min(len(items) - 1, selected + 1) if items else 0
            elif key in (curses.KEY_ENTER, 10, 13):
                if not items:
                    continue
                name, path, kind = items[selected]
                if kind == "dir":
                    current_dir = path
                    selected = 0
                    scroll = 0
                elif kind == "file":
                    result_path = None
                    while True:
                        action = file_action_menu(stdscr, path)
                        if action == "Open":
                            result_path = path
                            break
                        elif action == "Delete":
                            os.remove(path)
                            break
                        elif action == "Rename":
                            new_name = prompt_rename(stdscr, current_dir, path.name)
                            if new_name == "__CANCEL__" or not new_name:
                                continue
                            new_path = current_dir / new_name
                            if new_path.exists():
                                continue
                            path.rename(new_path)
                            break
                        else:
                            break
                    if result_path is not None:
                        return result_path
                    selected = min(selected, max(0, len(os.listdir(current_dir))))
                elif kind == "new":
                    fname = prompt_filename(stdscr, current_dir)
                    if fname == "__CANCEL__":
                        continue
                    if fname:
                        rel = Path(fname)
                        ext = rel.suffix
                        if ext not in SUPPORTED_EXTENSIONS:
                            continue
                        target_dir = current_dir / rel.parent
                        target_dir.mkdir(parents=True, exist_ok=True)
                        return target_dir / rel.name
                elif kind == "newdir":
                    dname = prompt_dirname(stdscr, current_dir)
                    if dname == "__CANCEL__" or not dname:
                        continue
                    new_dir_path = current_dir / dname
                    if new_dir_path.exists():
                        continue
                    new_dir_path.mkdir(parents=True, exist_ok=False)
                    selected = 0
                    scroll = 0
                elif kind == "renamedir":
                    parent = current_dir.parent
                    old_name = current_dir.name
                    new_name = prompt_dirname_rename(stdscr, parent, old_name)
                    if new_name == "__CANCEL__" or not new_name:
                        continue
                    new_path = parent / new_name
                    if new_path.exists():
                        continue
                    current_dir.rename(new_path)
                    current_dir = new_path
                    selected = 0
                    scroll = 0
                elif kind == "deletedir":
                    parent = current_dir.parent
                    current_dir.rmdir()
                    current_dir = parent
                    selected = 0
                    scroll = 0
            elif key == 27:
                return None

    return curses.wrapper(run)


def prompt_filename(stdscr, current_dir):
    curses.curs_set(1)
    buf = ""
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Create new note", curses.A_BOLD)
        label = f"New: {current_dir}/"
        stdscr.addstr(2, 0, label, curses.color_pair(1))
        stdscr.addstr(2, len(label), buf)

        footer = "Type a filename + Enter  |  Esc to cancel"
        h, w = stdscr.getmaxyx()
        stdscr.addstr(h - 1, 0, footer[:w-1], curses.A_DIM)
        stdscr.move(2, len(label) + len(buf))
        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_ENTER, 10, 13):
            return buf.strip() if buf.strip() else None
        elif key == 27:
            return "__CANCEL__"
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
        elif 32 <= key <= 126:
            buf += chr(key)


def prompt_dirname(stdscr, current_dir):
    curses.curs_set(1)
    buf = ""
    error = ""
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Create new directory", curses.A_BOLD)
        label = f"New dir: {current_dir}/"
        stdscr.addstr(2, 0, label, curses.color_pair(1))
        stdscr.addstr(2, len(label), buf)

        h, w = stdscr.getmaxyx()
        if error:
            stdscr.addstr(4, 0, error[:w-1], curses.A_BOLD)
        footer = "Letters, numbers, _ and - only  |  Enter to create  |  Esc to cancel"
        stdscr.addstr(h - 1, 0, footer[:w-1], curses.A_DIM)
        stdscr.move(2, len(label) + len(buf))
        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_ENTER, 10, 13):
            name = buf.strip()
            if not name:
                return None
            if not all(c.isalnum() or c in '_-' for c in name):
                error = "Invalid: only letters, numbers, _ and - allowed"
                continue
            return name
        elif key == 27:
            return "__CANCEL__"
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
            error = ""
        elif 32 <= key <= 126:
            buf += chr(key)
            error = ""


def prompt_dirname_rename(stdscr, parent_dir, old_name):
    curses.curs_set(1)
    buf = old_name
    error = ""
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Rename directory", curses.A_BOLD)
        label = f"Rename: {parent_dir}/"
        stdscr.addstr(2, 0, label, curses.color_pair(1))
        stdscr.addstr(2, len(label), buf)

        h, w = stdscr.getmaxyx()
        if error:
            stdscr.addstr(4, 0, error[:w-1], curses.A_BOLD)
        footer = "Letters, numbers, _ and - only  |  Enter to rename  |  Esc to cancel"
        stdscr.addstr(h - 1, 0, footer[:w-1], curses.A_DIM)
        stdscr.move(2, len(label) + len(buf))
        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_ENTER, 10, 13):
            name = buf.strip()
            if not name:
                return None
            if not all(c.isalnum() or c in '_-' for c in name):
                error = "Invalid: only letters, numbers, _ and - allowed"
                continue
            return name
        elif key == 27:
            return "__CANCEL__"
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
            error = ""
        elif 32 <= key <= 126:
            buf += chr(key)
            error = ""


def file_action_menu(stdscr, filepath):
    options = ["Open", "Delete", "Rename", "Cancel"]
    selected = 0
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "File options", curses.A_BOLD)
        stdscr.addstr(1, 0, f"File: {filepath.name}")
        for idx, opt in enumerate(options):
            prefix = "> " if idx == selected else "  "
            attr = curses.A_REVERSE if idx == selected else curses.A_NORMAL
            stdscr.addstr(idx + 3, 0, prefix + opt, attr)

        h, w = stdscr.getmaxyx()
        footer = "↑/↓ move  Enter select  Esc cancel"
        stdscr.addstr(h - 1, 0, footer[:w-1], curses.A_DIM)
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_UP:
            selected = max(0, selected - 1)
        elif key == curses.KEY_DOWN:
            selected = min(len(options) - 1, selected + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            return options[selected]
        elif key == 27:
            return "Cancel"


def prompt_rename(stdscr, current_dir, old_name):
    curses.curs_set(1)
    buf = old_name
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Rename note", curses.A_BOLD)
        label = f"Rename: {current_dir}/"
        stdscr.addstr(2, 0, label, curses.color_pair(1))
        stdscr.addstr(2, len(label), buf)

        h, w = stdscr.getmaxyx()
        footer = "Type new name + Enter  |  Esc to cancel"
        stdscr.addstr(h - 1, 0, footer[:w-1], curses.A_DIM)
        stdscr.move(2, len(label) + len(buf))
        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_ENTER, 10, 13):
            return buf.strip() if buf.strip() else None
        elif key == 27:
            return "__CANCEL__"
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
        elif 32 <= key <= 126:
            buf += chr(key)


if len(sys.argv) > 1:
    filepath = Path(sys.argv[1])
    if os.path.splitext(filepath)[1] not in SUPPORTED_EXTENSIONS:
        print("File not supported")
        quit()
    if os.path.exists(filepath):
        if os.path.getsize(filepath) > MAX_FILE_SIZE:
            print("File too large (max 500MB)")
            quit()
        with open(filepath, "r") as file:
            text = [line.rstrip('\n') for line in file.readlines()]
        if not text:
            text = [""]
    else:
        print("File doesn't exist")
        quit()
else:
    filepath = open_note_explorer(default_save_dir)
    if filepath is None:
        print("No file selected")
        quit()
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if filepath.exists():
        if os.path.getsize(filepath) > MAX_FILE_SIZE:
            print("File too large (max 500MB)")
            quit()
        with open(filepath, "r") as file:
            text = [line.rstrip('\n') for line in file.readlines()]
        if not text:
            text = [""]
    else:
        with open(filepath, "w") as file:
            file.write("")
        text = [""]

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

def scroll_to_cursor():
    if not (window_x[0] <= cursor[0] < window_x[1] and window_y[0] <= cursor[1] < window_y[1]):
        set_window()

def show_selections(origin, screen):
    x1, y1 = origin
    x2, y2 = cursor

    if (y1, x1) > (y2, x2):
        x1, y1, x2, y2 = x2, y2, x1, y1

    selections = []

    if y1 == y2:
        end = min(x2 + 1, len(text[y1]))
        selections.append((x1, y1, end - x1))
    else:
        selections.append((x1, y1, len(text[y1]) - x1))
        for y in range(y1 + 1, y2):
            selections.append((0, y, len(text[y])))
        end = min(x2 + 1, len(text[y2]))
        selections.append((0, y2, end))
    
    for x, y, length in selections:
        if window_y[0] <= y < window_y[1]:
            start_x = max(x, window_x[0])
            end_x = min(x + length, window_x[1])
            if start_x < end_x:
                rect = pygame.Rect((start_x - window_x[0]) * cw, (y - window_y[0]) * (ch + offset_), (end_x - start_x) * cw, ch)
                pygame.draw.rect(screen, (128, 128, 128), rect)

clipboard_lines = []

mode = "normal"
input_buffer = ""
last_pattern = ""
current_replacement = ""
status_message = ""

def get_selection_range(origin):
    x1, y1 = origin
    x2, y2 = cursor
    if (y1, x1) > (y2, x2):
        x1, y1, x2, y2 = x2, y2, x1, y1
    return x1, y1, x2, y2

def get_selection_lines(origin):
    x1, y1, x2, y2 = get_selection_range(origin)
    lines = []
    if y1 == y2:
        end = min(x2 + 1, len(text[y1]))
        lines.append(text[y1][x1:end])
    else:
        lines.append(text[y1][x1:])
        for y in range(y1 + 1, y2):
            lines.append(text[y])
        end = min(x2 + 1, len(text[y2]))
        lines.append(text[y2][:end])
    return lines

def delete_selection(origin):
    x1, y1, x2, y2 = get_selection_range(origin)
    if y1 == y2:
        end = min(x2 + 1, len(text[y1]))
        text[y1] = text[y1][:x1] + text[y1][end:]
    else:
        end = min(x2 + 1, len(text[y2]))
        text[y1] = text[y1][:x1] + text[y2][end:]
        del text[y1+1:y2+1]
    cursor[0] = x1
    cursor[1] = y1

def paste_lines(lines_list):
    if not lines_list:
        return
    if len(lines_list) == 1:
        seg = lines_list[0]
        text[cursor[1]] = text[cursor[1]][:cursor[0]] + seg + text[cursor[1]][cursor[0]:]
        cursor[0] += len(seg)
    else:
        tail = text[cursor[1]][cursor[0]:]
        head = text[cursor[1]][:cursor[0]] + lines_list[0]
        middle = lines_list[1:-1]
        last = lines_list[-1] + tail
        text[cursor[1]] = head
        text[cursor[1]+1:cursor[1]+1] = middle + [last]
        cursor[1] += len(lines_list) - 1
        cursor[0] = len(lines_list[-1])

def safe_copy_lines(lines_list):
    global clipboard_lines
    clipboard_lines = lines_list
    try:
        pyperclip.copy('\n'.join(lines_list))
    except pyperclip.PyperclipException:
        pass

def safe_paste_lines():
    global clipboard_lines
    try:
        ext = pyperclip.paste()
    except pyperclip.PyperclipException:
        return clipboard_lines

    if ext == '\n'.join(clipboard_lines):
        return clipboard_lines

    return ext.split('\n')

def compute_line_offsets_bytes():
    offsets = []
    offset = 0
    for line in text:
        offsets.append(offset)
        offset += len(line.encode('utf-8', errors='replace')) + 1
    return offsets

def offset_to_linecol_bytes(offset, line_offsets):
    i = bisect.bisect_right(line_offsets, offset) - 1
    i = max(0, min(i, len(line_offsets) - 1))
    byte_col = offset - line_offsets[i]
    line_bytes = text[i].encode('utf-8', errors='replace')
    char_col = len(line_bytes[:byte_col].decode('utf-8', errors='ignore'))
    return i, char_col

def cursor_byte_offset():
    line_offsets = compute_line_offsets_bytes()
    prefix_bytes = text[cursor[1]][:cursor[0]].encode('utf-8', errors='replace')
    return line_offsets[cursor[1]] + len(prefix_bytes)

def write_temp_snapshot():
    fd, tmp_path = tempfile.mkstemp(suffix=".searchtmp")
    with os.fdopen(fd, 'w') as f:
        f.write("\n".join(text))
    return tmp_path

def rg_search_next(pattern_str, from_line_col, wrap=True):
    if not RG_PATH:
        return None, "ripgrep not found"

    tmp_path = write_temp_snapshot()
    try:
        try:
            result = subprocess.run(
                [RG_PATH, "--json", "-e", pattern_str, tmp_path],
                capture_output=True, text=True, timeout=10
            )
        except subprocess.TimeoutExpired:
            return None, "Search timed out"
    finally:
        os.remove(tmp_path)

    if result.returncode not in (0, 1):
        return None, "Regex error"

    matches = []
    for line in result.stdout.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "match":
            continue
        data = obj["data"]
        line_no = data["line_number"] - 1
        for sm in data["submatches"]:
            matches.append((line_no, sm["start"]))

    if not matches:
        return None, "No matches found"

    from_line, from_col = from_line_col
    for (ln, col) in matches:
        if (ln, col) > (from_line, from_col):
            return (ln, col), None
    if wrap:
        return matches[0], None
    return None, "No matches found"

def build_text_mmap():
    data = "\n".join(text).encode('utf-8', errors='replace')
    size = max(len(data), 1)
    mm = mmap.mmap(-1, size)
    if data:
        mm.write(data)
        mm.seek(0)
    return mm, len(data)

def mmap_find_next(pattern_str, from_offset):
    mm, size = build_text_mmap()
    try:
        try:
            pattern = re.compile(pattern_str.encode('utf-8'), re.MULTILINE)
        except re.error as e:
            return None, f"Invalid regex: {e}"
        buf = mm[:size]
        m = pattern.search(buf, from_offset)
        if not m:
            return None, "Replace complete"
        return m, None
    finally:
        mm.close()

def mmap_replace_all(pattern_str, replacement):
    mm, size = build_text_mmap()
    try:
        try:
            pattern = re.compile(pattern_str.encode('utf-8'), re.MULTILINE)
        except re.error as e:
            return None, f"Invalid regex: {e}"
        buf = mm[:size]
        new_buf, count = pattern.subn(replacement.encode('utf-8'), buf)
        text[:] = new_buf.decode('utf-8', errors='replace').split('\n')
        return count, None
    finally:
        mm.close()

def mmap_apply_single(m, replacement):
    mm, size = build_text_mmap()
    try:
        buf = mm[:size]
        replaced_bytes = m.expand(replacement.encode('utf-8'))
        new_buf = buf[:m.start()] + replaced_bytes + buf[m.end():]
        text[:] = new_buf.decode('utf-8', errors='replace').split('\n')
        return m.start() + len(replaced_bytes)
    finally:
        mm.close()

def parse_substitute_command(cmd):
    if not cmd.startswith('s/'):
        return None
    body = cmd[2:]
    parts, current, i = [], '', 0
    while i < len(body):
        if body[i] == '\\' and i + 1 < len(body) and body[i+1] == '/':
            current += '/'
            i += 2
        elif body[i] == '/':
            parts.append(current)
            current = ''
            i += 1
        else:
            current += body[i]
            i += 1
    parts.append(current)
    if len(parts) < 2:
        return None
    pattern = parts[0]
    replacement = parts[1]
    flags = parts[2] if len(parts) > 2 else ''
    return pattern, replacement, flags

dialog_surface = pygame.Surface((300,100))
unsaved_dialog = unsavedDialog(dialog_surface)

while running:
    screen.fill((32,32,32))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if mode != "normal":
                if event.key == pygame.K_ESCAPE:
                    mode = "normal"
                    input_buffer = ""
                    status_message = ""
                elif mode == "search_input":
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        last_pattern = input_buffer
                        input_buffer = ""
                        match, err = rg_search_next(last_pattern, (cursor[1], cursor[0]), wrap=True)
                        if match:
                            cursor[1], cursor[0] = match
                            scroll_to_cursor()
                            text_surface = render_window()
                            status_message = ""
                        else:
                            status_message = err
                        mode = "normal"
                    elif event.key in (pygame.K_BACKSPACE, 127, 8):
                        input_buffer = input_buffer[:-1]
                    elif event.unicode.isprintable():
                        input_buffer += event.unicode
                elif mode == "command_input":
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        cmd = input_buffer
                        input_buffer = ""
                        parsed = parse_substitute_command(cmd)
                        if not parsed:
                            status_message = "Bad command (use s/pattern/replacement/[g])"
                            mode = "normal"
                        else:
                            pattern, replacement, flags = parsed
                            if 'g' in flags:
                                pygame.display.set_caption(caption + "*")
                                count, err = mmap_replace_all(pattern, replacement)
                                text_surface = render_window()
                                status_message = err if err else f"Replaced {count} occurrence(s)"
                                mode = "normal"
                            else:
                                last_pattern = pattern
                                current_replacement = replacement
                                m, err = mmap_find_next(pattern, 0)
                                if not m:
                                    status_message = err
                                    mode = "normal"
                                else:
                                    line_offsets = compute_line_offsets_bytes()
                                    cursor[1], cursor[0] = offset_to_linecol_bytes(m.start(), line_offsets)
                                    scroll_to_cursor()
                                    text_surface = render_window()
                                    mode = "replace_one_wait"
                    elif event.key in (pygame.K_BACKSPACE, 127, 8):
                        input_buffer = input_buffer[:-1]
                    elif event.unicode.isprintable():
                        input_buffer += event.unicode
                elif mode == "replace_one_wait":
                    if event.key in (pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
                        m, err = mmap_find_next(last_pattern, cursor_byte_offset())
                        if m:
                            pygame.display.set_caption(caption + "*")
                            next_offset = mmap_apply_single(m, current_replacement)
                            text_surface = render_window()
                            nm, nerr = mmap_find_next(last_pattern, next_offset)
                            if nm:
                                line_offsets = compute_line_offsets_bytes()
                                cursor[1], cursor[0] = offset_to_linecol_bytes(nm.start(), line_offsets)
                                scroll_to_cursor()
                            else:
                                status_message = "Replace complete"
                                mode = "normal"
                        else:
                            status_message = "Replace complete"
                            mode = "normal"
                    elif event.key in (pygame.K_n, pygame.K_SPACE):
                        m, err = mmap_find_next(last_pattern, cursor_byte_offset())
                        if m:
                            nm, nerr = mmap_find_next(last_pattern, m.end())
                            if nm:
                                line_offsets = compute_line_offsets_bytes()
                                cursor[1], cursor[0] = offset_to_linecol_bytes(nm.start(), line_offsets)
                                scroll_to_cursor()
                            else:
                                status_message = "Replace complete"
                                mode = "normal"
                        else:
                            status_message = "Replace complete"
                            mode = "normal"
                continue

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
                if cy <= window_y[0]+3 and cy > 0:
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
                if cy >= window_y[1]-3 and cy > 0:
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
            elif event.key == pygame.K_BACKSPACE and unsaved_exit == False and selection == False:
                pygame.display.set_caption(caption + "*")
                if cursor[0] > 0 and text[cursor[1]]:
                    text[cursor[1]] = text[cursor[1]][:cursor[0]-1] + text[cursor[1]][cursor[0]:]
                    if cursor[0] <= window_x[0]+3:
                        if window_x[0] > 0:
                            slide_x(-1)
                    cursor[0] -= 1
                    cursor[0] = max(0, cursor[0])
                    text_surface = render_window()
                elif cursor[0] == 0 and cursor[1] <= window_y[0]+3 and cursor[1] > 0:
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
            elif event.key == pygame.K_TAB and unsaved_exit == False and selection == False:
                pygame.display.set_caption(caption + "*")
                text[cursor[1]] = text[cursor[1]][:cursor[0]] + " "*4 + text[cursor[1]][cursor[0]:]
                if cursor[0] > window_x[1]-4:
                    w1 = window_x[1]
                    slide_x(4-(w1 - cursor[0]))
                cursor[0] += 4
                text_surface = render_window()
            elif event.key == pygame.K_SPACE and unsaved_exit == False and selection == False:
                pygame.display.set_caption(caption + "*")
                text[cursor[1]] = text[cursor[1]][:cursor[0]] + " " + text[cursor[1]][cursor[0]:]
                if cursor[0] == window_x[1]:
                    slide_x(1)
                cursor[0] += 1
                text_surface = render_window()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and unsaved_exit == False and selection == False:
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
            elif event.key == pygame.K_o and (event.mod & pygame.KMOD_CTRL) and (event.mod & pygame.KMOD_SHIFT) and unsaved_exit == False and selection == False:
                pygame.display.set_caption(caption + "*")
                text.insert(cursor[1] + 1, "")
                cursor[1] += 1
                cursor[0] = 0
                scroll_to_cursor()
                text_surface = render_window()
            elif event.key == pygame.K_o and (event.mod & pygame.KMOD_CTRL) and unsaved_exit == False and selection == False:
                pygame.display.set_caption(caption + "*")
                text.insert(cursor[1], "")
                cursor[0] = 0
                scroll_to_cursor()
                text_surface = render_window()
            elif event.key == pygame.K_d and (event.mod & pygame.KMOD_CTRL) and unsaved_exit == False and selection == False:
                pygame.display.set_caption(caption + "*")
                y = cursor[1]
                del text[y]
                if not text:
                    text.append("")
                cursor[1] = max(0, min(y - 1, len(text) - 1))
                cursor[0] = 0
                scroll_to_cursor()
                text_surface = render_window()
            elif event.key == pygame.K_b and (event.mod & pygame.KMOD_CTRL) and unsaved_exit == False:
                cursor[0] = 0
                scroll_to_cursor()
                text_surface = render_window()
            elif event.key == pygame.K_e and (event.mod & pygame.KMOD_CTRL) and unsaved_exit == False:
                cursor[0] = len(text[cursor[1]])
                scroll_to_cursor()
                text_surface = render_window()
            elif event.key == pygame.K_c and selection and unsaved_exit == False:
                safe_copy_lines(get_selection_lines(sel_origin))
                selection = False
                sel_origin = None
            elif event.key == pygame.K_x and selection and unsaved_exit == False:
                pygame.display.set_caption(caption + "*")
                safe_copy_lines(get_selection_lines(sel_origin))
                delete_selection(sel_origin)
                selection = False
                sel_origin = None
                scroll_to_cursor()
                text_surface = render_window()
            elif event.key == pygame.K_p and selection and unsaved_exit == False:
                pygame.display.set_caption(caption + "*")
                delete_selection(sel_origin)
                selection = False
                sel_origin = None
                paste_lines(safe_paste_lines())
                scroll_to_cursor()
                text_surface = render_window()
            elif event.key == pygame.K_p and (event.mod & pygame.KMOD_CTRL) and unsaved_exit == False:
                pygame.display.set_caption(caption + "*")
                paste_lines(safe_paste_lines())
                scroll_to_cursor()
                text_surface = render_window()
            elif event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL) and unsaved_exit == False:
                selection = not selection
                if selection:
                    sel_origin = (cursor[0], cursor[1])
                else:
                    sel_origin = None
            elif event.key == pygame.K_f and (event.mod & pygame.KMOD_CTRL) and unsaved_exit == False:
                mode = "search_input"
                input_buffer = ""
                status_message = ""
                selection = False
                sel_origin = None
            elif event.key == pygame.K_r and (event.mod & pygame.KMOD_CTRL) and unsaved_exit == False:
                mode = "command_input"
                input_buffer = ""
                status_message = ""
                selection = False
                sel_origin = None
            elif event.key == pygame.K_n and (event.mod & pygame.KMOD_CTRL) and unsaved_exit == False and selection == False:
                if last_pattern:
                    match, err = rg_search_next(last_pattern, (cursor[1], cursor[0]), wrap=True)
                    if match:
                        cursor[1], cursor[0] = match
                        scroll_to_cursor()
                        text_surface = render_window()
                        status_message = ""
                    else:
                        status_message = err
            elif event.mod & pygame.KMOD_CTRL:
                pass
            else:
                if unsaved_exit == False and selection == False and event.unicode.isprintable():
                    new_text = text[cursor[1]][:cursor[0]] + event.unicode + text[cursor[1]][cursor[0]:]
                    if len(new_text) != len(text[cursor[1]]):
                        pygame.display.set_caption(caption + "*")
                        text[cursor[1]] = new_text
                        if cursor[0] == window_x[1]:
                            slide_x(1)
                        cursor[0] += 1
                        text_surface = render_window()

    pygame.draw.rect(screen, (64, 64, 64), (0, (ch+offset_)*(cursor[1]-window_y[0]), WIDTH, ch))
    if selection == True:
        show_selections(sel_origin, screen)
    pygame.draw.rect(screen, cursor_color, (cw*(cursor[0]-window_x[0]), (ch+offset_)*(cursor[1]-window_y[0]), cw, ch), 2)
    screen.blit(text_surface, (0,0))

    if mode == "search_input":
        bar = dialog_font.render(f"Find:{input_buffer}", False, (0,0,0), bgcolor=(200,200,0))
        screen.blit(bar, (0, HEIGHT-20))
    elif mode == "command_input":
        bar = dialog_font.render(f"Find-Replace:{input_buffer}", False, (0,0,0), bgcolor=(200,200,0))
        screen.blit(bar, (0, HEIGHT-20))
    elif mode == "replace_one_wait":
        bar = dialog_font.render("Replace? y=yes  n=skip  Esc=stop", False, (0,0,0), bgcolor=(200,200,0))
        screen.blit(bar, (0, HEIGHT-20))
    elif status_message:
        bar = dialog_font.render(status_message, False, (0,0,0), bgcolor=(0,150,0))
        screen.blit(bar, (0, HEIGHT-20))

    if unsaved_exit == True:
        screen.blit(unsaved_dialog, ((WIDTH//2)-150, (HEIGHT//2)-50))

    pygame.display.update()
    clock.tick(60)

pygame.quit()