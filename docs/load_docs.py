from talon import actions, scope, cron, app, ui, Context, Module, speech_system
import os

def load_documentation():
    # Check if Talon HUD is available to the user
    TALON_HUD_RELEASE_PERSISTENT = 6
    if "user.talon_hud_available" in scope.get("tag") and \
        scope.get("user.talon_hud_version") != None and scope.get("user.talon_hud_version") >= TALON_HUD_RELEASE_PERSISTENT:
    
        # Get the absolute path to the documentation directory for your package
        documentation_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Add an item to the Toolkit documentation page
        actions.user.hud_add_documentation("Speed dial commands", 
            "shows the available commands used to generate speed dials on the fly.",
            os.path.join(documentation_dir, "speed_dial_documentation.md"))

app.register("ready", load_documentation)