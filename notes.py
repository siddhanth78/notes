import pygame
# from suggest import Tree

pygame.init()

all_monitors = pygame.display.get_desktop_sizes()

WIDTH, HEIGHT = all_monitors[0][0], all_monitors[0][1] - 100

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.key.set_repeat(200, 50)

cw, ch = 10, 16
offset_ = 4

font = pygame.font.SysFont("firacodemedium", 16)

window_x = [0, (WIDTH//cw) - 1]
window_y = [0, (HEIGHT//(ch+offset_)) - 1]

text = [""]
w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
all_text = '\n'.join(w_text)

text_color = (255,255,255)
cursor_color = (128,128,128)

text_surface = font.render(all_text, False, text_color)
cursor = [0,0]

clock = pygame.time.Clock()

running = True

while running:
    screen.fill((32,32,32))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_LEFT:
                cx = cursor[0]
                if cx == window_x[0]+3 and cx > 0:
                    if window_x[0] > 0:
                        window_x[0] -= 1
                        window_x[1] -= 1
                        w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
                        all_text = '\n'.join(w_text)
                        text_surface = font.render(all_text, False, text_color)
                cursor[0] = max(0, cx-1) 
            elif event.key == pygame.K_RIGHT:
                cx = cursor[0]
                if cx >= window_x[1]-3 and cx > 0:
                    if window_x[1] < len(text[cursor[1]]):
                        window_x[0] += 1
                        window_x[1] += 1
                        w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
                        all_text = '\n'.join(w_text)
                        text_surface = font.render(all_text, False, text_color)
                cursor[0] = min(len(text[cursor[1]]), cx+1)
            elif event.key == pygame.K_UP:
                cy = cursor[1]
                if cy == window_y[0]+3 and cy > 0:
                    if window_y[0] > 0:
                        window_y[0] -= 1
                        window_y[1] -= 1
                        w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
                        all_text = '\n'.join(w_text)
                        text_surface = font.render(all_text, False, text_color)
                cursor[1] = max(0, cy-1)
                cursor[0] = min(len(text[cursor[1]]), cursor[0]) 
            elif event.key == pygame.K_DOWN:
                cy = cursor[1]
                cursor[1] = min(len(text)-1, cy+1)
                if cy == window_y[1]-3 and cy > 0:
                    if window_y[1] < len(text):
                        window_y[0] += 1
                        window_y[1] += 1
                        w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
                        all_text = '\n'.join(w_text)
                        text_surface = font.render(all_text, False, text_color)
                cursor[0] = min(len(text[cursor[1]]), cursor[0]) 
            elif event.key == pygame.K_BACKSPACE:
                if cursor[0] > 0 and text[cursor[1]]:
                    text[cursor[1]] = text[cursor[1]][:cursor[0]-1] + text[cursor[1]][cursor[0]:]
                    if cursor[0] <= window_x[0]+3:
                        if window_x[0] > 0:
                            window_x[0] -= 1
                            window_x[1] -= 1
                    cursor[0] -= 1
                    cursor[0] = max(0, cursor[0])
                    w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
                    all_text = '\n'.join(w_text)
                    text_surface = font.render(all_text, False, text_color)
                elif cursor[0] == 0 and cursor[1] == window_y[0]+3 and cursor[1] > 0:
                    if window_y[0] > 0:
                        window_y[0] -= 1
                        window_y[1] -= 1
                    cursor[0] = len(text[cursor[1]-1])
                    popped = text.pop(cursor[1])
                    text[cursor[1]-1] += popped
                    if len(text[cursor[1]-1]) > (WIDTH//cw)-1:
                        window_x[0] += len(text[cursor[1]-1]) - ((WIDTH//cw)-1) - len(popped)
                        window_x[1] += len(text[cursor[1]-1]) - ((WIDTH//cw)-1) - len(popped)
                    cursor[1] -= 1
                    w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
                    all_text = '\n'.join(w_text)
                    text_surface = font.render(all_text, False, text_color)
                elif cursor[0] == 0 and cursor[1]>0:
                    cursor[0] = len(text[cursor[1]-1])
                    popped = text.pop(cursor[1])
                    text[cursor[1]-1] += popped
                    if len(text[cursor[1]-1]) > (WIDTH//cw)-1:
                        window_x[0] += len(text[cursor[1]-1]) - ((WIDTH//cw)-1) - len(popped)
                        window_x[1] += len(text[cursor[1]-1]) - ((WIDTH//cw)-1) - len(popped)
                    cursor[1] -= 1
                    w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
                    all_text = '\n'.join(w_text)
                    text_surface = font.render(all_text, False, text_color)
            elif event.key == pygame.K_TAB:
                text[cursor[1]] = text[cursor[1]][:cursor[0]] + " "*4 + text[cursor[1]][cursor[0]:]
                if cursor[0] > window_x[1]-4:
                    w1 = window_x[1]
                    window_x[1] += 4-(w1 - cursor[0])
                    window_x[0] += 4-(w1 - cursor[0])
                cursor[0] += 4
                w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
                all_text = '\n'.join(w_text)
                text_surface = font.render(all_text, False, text_color)
            elif event.key == pygame.K_SPACE:
                text[cursor[1]] = text[cursor[1]][:cursor[0]] + " " + text[cursor[1]][cursor[0]:]
                if cursor[0] == window_x[1]:
                    window_x[0] += 1
                    window_x[1] += 1
                cursor[0] += 1
                w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
                all_text = '\n'.join(w_text)
                text_surface = font.render(all_text, False, text_color)
            elif event.key == pygame.K_RETURN:
                text.insert(cursor[1]+1, "")
                text[cursor[1]+1] = text[cursor[1]][cursor[0]:]
                text[cursor[1]] = text[cursor[1]][:cursor[0]]
                cursor[1] += 1
                cursor[0] = 0
                if cursor[1] == window_y[1]:
                    window_y[0] += 1
                    window_y[1] += 1
                window_x[0] = 0
                window_x[1] = (WIDTH//cw)-1
                w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
                all_text = '\n'.join(w_text)
                text_surface = font.render(all_text, False, text_color)
            else:
                new_text = text[cursor[1]][:cursor[0]] + event.unicode + text[cursor[1]][cursor[0]:]
                if len(new_text) != len(text[cursor[1]]):
                    text[cursor[1]] = new_text
                    if cursor[0] == window_x[1]:
                        window_x[0] += 1
                        window_x[1] += 1
                    cursor[0] += 1
                w_text = [wt[window_x[0]:window_x[1]] for wt in text[window_y[0]:window_y[1]]]
                all_text = '\n'.join(w_text)
                text_surface = font.render(all_text, False, text_color)

    
    pygame.draw.rect(screen, cursor_color, (cw*(cursor[0]-window_x[0]), (ch+offset_)*(cursor[1]-window_y[0]), cw, ch), 2)
    screen.blit(text_surface, (0,0))
    pygame.display.update()
    clock.tick(60)

pygame.quit()
