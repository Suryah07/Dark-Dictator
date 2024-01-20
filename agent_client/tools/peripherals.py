from pynput import keyboard, mouse

input_blocked = False

def block():
    try:
        if not input_blocked:
            async def on_press():
                pass
            async def on_release():
                pass
            async def on_click():
                pass
            keyboard_listener = keyboard.Listener(suppress=True)
            mouse_listener = mouse.Listener(suppress=True)
            keyboard_listener.start()
            mouse_listener.start()
            input_blocked = True
            return "Blocked"
        else:
            return "Already Blocked"
    except Exception as e:
        print("error",e)
        return e

def unblock():
    try:
        if input_blocked:
            keyboard_listener.stop()
            mouse_listener.stop()
            input_blocked = False
            return "UnBlocked"
        else:
            return "Already UnBlocked"
    except Exception as e:
        print("err",e)
        return e