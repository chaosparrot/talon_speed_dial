from talon import noise, actions, Module
from talon_plugins import eye_mouse, eye_zoom_mouse 

mod = Module()
pop_enabled = True

def speed_dial_on_pop(active):
    global pop_enabled
    if pop_enabled and not eye_zoom_mouse.zoom_mouse.enabled or eye_mouse.mouse.attached_tracker is None:
        actions.user.speed_dial_activate(None, 'pop')

# Remove the # in front of the line below to allow pop to activate the first speed dial
#noise.register("pop", speed_dial_on_pop)

@mod.action_class
class Actions:

    def speed_dial_toggle_pop(enabled: int = -1):
        """Toggle the pop noise from being on or off"""
        global pop_enabled
        if enabled == -1:
            pop_enabled = not pop_enabled
        else:
            pop_enabled = enabled > 0