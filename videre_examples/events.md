# Handled
```
QUIT              none
MOUSEBUTTONDOWN   pos, button, touch
MOUSEBUTTONUP     pos, button, touch
MOUSEWHEEL        which, flipped, x, y, touch, precise_x, precise_y
MOUSEMOTION       pos, rel, buttons, touch
WINDOWLEAVE       Mouse left the window
WINDOWRESIZED     Window got resized
TEXTINPUT         text
KEYDOWN           key, mod, unicode, scancode
```

# Deprecated
```
ACTIVEEVENT       gain, state
    WINDOWEVENT
VIDEORESIZE       size, w, h
    WINDOWEVENT
VIDEOEXPOSE       none
    WINDOWEVENT
```

# To handle
```
KEYUP             key, mod, unicode, scancode
JOYAXISMOTION     joy (deprecated), instance_id, axis, value
JOYBALLMOTION     joy (deprecated), instance_id, ball, rel
JOYHATMOTION      joy (deprecated), instance_id, hat, value
JOYBUTTONUP       joy (deprecated), instance_id, button
JOYBUTTONDOWN     joy (deprecated), instance_id, button
USEREVENT         code

# SDL2
AUDIODEVICEADDED   which, iscapture (SDL backend >= 2.0.4)
AUDIODEVICEREMOVED which, iscapture (SDL backend >= 2.0.4)
FINGERMOTION       touch_id, finger_id, x, y, dx, dy
FINGERDOWN         touch_id, finger_id, x, y, dx, dy
FINGERUP           touch_id, finger_id, x, y, dx, dy
MULTIGESTURE       touch_id, x, y, pinched, rotated, num_fingers
TEXTEDITING        text, start, length

DROPFILE                 file
DROPBEGIN                (SDL backend >= 2.0.5)
DROPCOMPLETE             (SDL backend >= 2.0.5)
DROPTEXT                 text (SDL backend >= 2.0.5)
MIDIIN
MIDIOUT
CONTROLLERDEVICEADDED    device_index
JOYDEVICEADDED           device_index
CONTROLLERDEVICEREMOVED  instance_id
JOYDEVICEREMOVED         instance_id
CONTROLLERDEVICEREMAPPED instance_id
KEYMAPCHANGED            (SDL backend >= 2.0.4)
CLIPBOARDUPDATE
RENDER_TARGETS_RESET     (SDL backend >= 2.0.2)
RENDER_DEVICE_RESET      (SDL backend >= 2.0.4)
LOCALECHANGED            (SDL backend >= 2.0.14)

# pygame 2.0.1
WINDOWSHOWN            Window became shown
WINDOWHIDDEN           Window became hidden
WINDOWEXPOSED          Window got updated by some external event
WINDOWMOVED            Window got moved
WINDOWSIZECHANGED      Window changed its size
WINDOWMINIMIZED        Window was minimized
WINDOWMAXIMIZED        Window was maximized
WINDOWRESTORED         Window was restored
WINDOWENTER            Mouse entered the window
WINDOWFOCUSGAINED      Window gained focus
WINDOWFOCUSLOST        Window lost focus
WINDOWCLOSE            Window was closed
WINDOWTAKEFOCUS        Window was offered focus (SDL backend >= 2.0.5)
WINDOWHITTEST          Window has a special hit test (SDL backend >= 2.0.5)
WINDOWICCPROFCHANGED   Window ICC profile changed (SDL backend >= 2.0.18)
WINDOWDISPLAYCHANGED   Window moved on a new display (SDL backend >= 2.0.18)

# Android
APP_TERMINATING           OS is terminating the application
APP_LOWMEMORY             OS is low on memory, try to free memory if possible
APP_WILLENTERBACKGROUND   Application is entering background
APP_DIDENTERBACKGROUND    Application entered background
APP_WILLENTERFOREGROUND   Application is entering foreground
APP_DIDENTERFOREGROUND    Application entered foreground
```

# Pieces of code

Basic pygame loop:
```python
import pygame

pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print("Quit pygame.")
            running = False
    screen.fill("white")
    pygame.display.flip()
    clock.tick(60)
pygame.quit()
```

# Mouse event management
```
down( dépend d'un button)
	enter (down move)
	move (down move)
	up
		this widget (up, click)
		other widget (down canceled)
	exit (down move)

DOWN	OWNER
None	None
None	owner	owner->up
down	None								down->down_canceled
owner	owner	owner->up	owner->click
down	owner	owner->up					down->down_canceled
```
