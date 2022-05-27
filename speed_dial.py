from talon import actions, scope, cron, app, ui, Context, Module, speech_system
import os
from typing import Union
from talon.grammar import Phrase

mod = Module()
ctx = Context()
mod.list("speed_dial_names", desc="List of names of all the available speed dials")
mod.tag("speed_dial_shortcuts", desc="Whether or not the speed dial shortcuts are enabled")
mod.tag("speed_dial_noises", desc="Whether or not the speed dial noises are enabled")

dirname = os.path.dirname(os.path.realpath(__file__))

class SpeedDialManager:
    hud_available = False
    speed_dials = None
    default_dial = None
    dial_config_menu = None
    speed_dials_set = None
    
    max_phrases = 40
    available_phrases = None
    next_commands_dict = None
    allow_listening = True
    sleep_job = None
    shortcuts_enabled = True
    noises_enabled = True
    dial_job = None

    # Talon HUD variables
    enabled = False
    content = None

    def __init__(self, speed_dials):
        self.speed_dials = speed_dials
        self.available_phrases = []
        self.next_commands_dict = {}
        self.speed_dials_set = set([])
        
        speeddial_list = []
        for name in self.speed_dials:
            speeddial_list.append(name)
        ctx.lists["user.speed_dial_names"] = speeddial_list
        self.default_dial = speeddial_list[0]
        
        # Check if the HUD is available
        TALON_HUD_RELEASE_PERSISTENCE = 6
        self.hud_available = "user.talon_hud_available" in scope.get("tag") and \
            scope.get("user.talon_hud_version") != None and scope.get("user.talon_hud_version") >= TALON_HUD_RELEASE_PERSISTENCE

        speech_system.register("pre:phrase", self.check_phrase)
        self.sleep_job = cron.interval("500ms", self.check_mode)
        if self.hud_available:
            actions.user.hud_add_poller("speed_dial", self, True)
            actions.user.hud_activate_poller("speed_dial")
            self.dial_config_menu = SpeedDialConfigurationMenu(self)
            actions.user.hud_add_poller("speed_dial_options", self.dial_config_menu)

    def activate_dial(self, dial: str = None, type: str = "voice"):
        if dial is None:
            dial = self.default_dial

        if dial in self.speed_dials and len(self.speed_dials[dial]["commands"]) > 0:
            if self.hud_available and self.enabled:
                self.hud_update_status_icon(dial, True, type == "mouseclick")
            if type == "keystroke":
                actions.sleep(0.1)
            cron.after("100ms", lambda self=self, dial=dial: self.run_dial_commands(dial))

    def run_dial_commands(self, dial):
        active_app = ui.active_app().name
        active_app_changed = False
        for command in self.speed_dials[dial]["commands"]:
            actions.sleep(0.1 if not active_app_changed else 0.25)
            # Talon Speed dial mimics the commands here - If an error occurred, you might be in the wrong context for that command
            actions.mimic(command)
            active_app_changed = ui.active_app().name != active_app
            if active_app_changed:
                active_app = ui.active_app().name

        if self.hud_available and self.enabled:
            self.hud_update_status_icon(dial, False, type == "mouseclick")

    def configure_dial(self, commands: list[str] = None, dial: str = None):
        global dirname
        if dial is None:
            dial = self.default_dial
        if commands is None:
            commands = []
            
        if dial in self.speed_dials:
            previous_commands = self.speed_dials[dial]["commands"]
            self.speed_dials[dial]["commands"] = commands
            
            if self.hud_available and self.enabled:
                status_bar_topic = "speed_dial_" + dial

                if len(commands) > 0:
                    actions.user.hud_add_log("event", "Dial " + dial + " set!\n" + "; ".join(commands))
                    self.hud_update_status_icon(dial)
                else:
                    if previous_commands is not None and len(previous_commands) > 0:
                        actions.user.hud_add_log("event", "Dial " + dial + " cleared!")
                        self.content.publish_event("status_icons", status_bar_topic, "remove")
                
                self.hud_update_dial_options()
            
            # Handle enabling of shortcuts if dials are active
            if len(commands) > 0:
                self.speed_dials_set.add(dial)
            elif dial in self.speed_dials_set:
                self.speed_dials_set.remove(dial)
            self.toggle_keyboard_shortcuts(len(self.speed_dials_set) > 0, False)

    def configure_dial_last_commands(self, dial = None, previous_commands: int = 1):
        commands = []
        for phrase in reversed(self.available_phrases):
            commands.append(phrase)
            if len(commands) >= previous_commands:
                break
        
        self.configure_dial(list(reversed(commands)), dial)
        
    def configure_dial_next_commands(self, dial = None, next_commands_amount: int = 1):
        if dial is None:
            dial = self.default_dial
        if dial in self.speed_dials and next_commands_amount > 0:
            self.next_commands_dict[dial] = {
                "commands": [],
                "amount": next_commands_amount
            }

    def check_phrase(self, phrase):
        # Only allow speech commands during non-sleep modes
        if self.allow_listening and "text" in phrase and "_metadata" in phrase:        
            full_command = " ".join(phrase["text"])
            
            # Remove commands starting with speed dial to prevent those commands from clogging up the available phrases
            if not full_command.startswith("speed dial"):
                voice_command = full_command.split(" speed dial")[0]
                if voice_command:
                    self.available_phrases.append(voice_command)
                    self.available_phrases = self.available_phrases[-self.max_phrases:]
                
                # Apply voice commands for macros set up in advance
                if voice_command and len(self.next_commands_dict) > 0:
                    dial_list = list(self.next_commands_dict.keys())
                    for dial in dial_list:
                        next_command_def = self.next_commands_dict[dial]
                        next_command_def["commands"].append(voice_command)
                        if len(next_command_def["commands"]) >= next_command_def["amount"]:
                            self.configure_dial(next_command_def["commands"], dial)
                            del self.next_commands_dict[dial]
                        else:
                            self.next_commands_dict[dial] = next_command_def

    def force_add_phrase(self, phrase):
        if phrase:
            self.available_phrases.append(phrase)
            self.available_phrases = self.available_phrases[-self.max_phrases:]

    def check_mode(self):
        previous_allow_listening = self.allow_listening
        self.allow_listening = actions.speech.enabled()
        
        # Make sure to keep the status bar icons consistent
        if previous_allow_listening != self.allow_listening and self.hud_available:
            for dial in self.speed_dials:
                if len(self.speed_dials[dial]["commands"]) == 0:
                    continue

                if self.allow_listening:
                    self.hud_update_status_icon(dial)
                else:
                    self.content.publish_event("status_icons", "speed_dial_" + dial, "remove")

    def clear_dials(self): 
        for speed_dial in self.speed_dials:
            self.configure_dial([], speed_dial)
        self.next_commands_list = {}

    # Talon HUD methods
    def hud_generate_speed_dial_function(self, dial):
        return lambda _, _2, dial=dial, speedial=self: speedial.activate_dial(dial, "mouseclick")

    def hud_update_status_icon(self, dial, activated = False, clicked = False):
        # Make sure the window does not lose focus when clicking on the status icon
        if clicked:
            ui.active_window().focus()

        image_name = self.speed_dials[dial]["icon"]
        image = os.path.join(dirname, "images", "active_" + image_name if activated else image_name)
        status_icon = self.content.create_status_icon("speed_dial_" + dial, image, None, "Speed dial " + dial, self.hud_generate_speed_dial_function(dial) )
        self.content.publish_event("status_icons", status_icon.topic, "replace", status_icon)        

    def enable(self):
        if not self.enabled:
           self.enabled = True

    def disable(self):
        if self.enabled:
            self.enabled = False
            speech_system.unregister("pre:phrase", self.check_phrase)
            cron.cancel(self.sleep_job)

    def open_hud_options_menu(self):
        actions.user.hud_activate_poller("speed_dial_options")
        
    def hud_update_dial_options(self, initial=False):
        self.dial_config_menu.update_dials(False)
        
    def toggle_keyboard_shortcuts(self, enabled = None, persistent = True):
        if enabled == None:
            enabled = not self.shortcuts_enabled
        
        if persistent:
            self.shortcuts_enabled = enabled == True
            if self.hud_available and self.enabled:
                actions.user.hud_add_log("event", "Speed dial shortcuts " + ( "enabled" if self.shortcuts_enabled else "disabled" ))

        tags = []
        if enabled:
            tags.append("user.speed_dial_shortcuts")
        if self.noises_enabled:
            tags.append("user.speed_dial_noises")
        ctx.tags = tags

    def toggle_noises(self, enabled = None):
        if enabled == None:
            enabled = not self.noises_enabled
        self.noises_enabled = enabled
        self.toggle_keyboard_shortcuts(len(self.speed_dials_set) > 0, False)

class SpeedDialConfigurationMenu:
    enabled = False
    content = None
    speed_dial_manager = None
    
    def __init__(self, speed_dial_manager):
        self.speed_dial_manager = speed_dial_manager
    
    def enable(self):
        if not self.enabled:
           self.enabled = True
           self.update_dials(True)

    def disable(self):
        if self.enabled:
            self.enabled = False

    def destroy(self):
        self.disable()
        self.speed_dial_manager = None

    def update_dials(self, initial):
        if not self.enabled:
            return

        choices = []
        for dial in self.speed_dial_manager.speed_dials:
            commands = "; ".join(self.speed_dial_manager.speed_dials[dial]["commands"])
            dial_name = "Dial " + dial
            if len(commands) > 0:
                dial_name += " - " + commands
        
            dial_choice = {"text": dial_name, "dial": dial, "selected": len(commands) > 0}
            choices.append(dial_choice)
        
        hud_choices = self.content.create_choices(choices, self.select_hud_dial)
        content_text = "Configure a speed dial by saying <*option <number>/>"
        choice_panel_content = self.content.create_panel_content(content_text, "speed_dial_options", "Speed dial options", initial, choices=hud_choices)
        self.content.publish_event("choice", "speed_dial_options", "replace", choice_panel_content)

    def select_hud_dial(self, selected_dial = None):
        if selected_dial != None:
            if len(self.speed_dial_manager.available_phrases) == 0:
                actions.user.hud_add_log("warning", "No phrases are available to configure yet!")
                return
            
            choices = []
            for phrase in self.speed_dial_manager.available_phrases:            
                phrase_choice = {"text": phrase, "dial": selected_dial["dial"], "phrase": phrase}
                choices.append(phrase_choice)
            hud_choices = self.content.create_choices(choices, self.select_hud_phrases, True)
            content_text = "Select one or more phrases using <*option <number>/>"
            choice_panel_content = self.content.create_panel_content(content_text, "speed_dial_configure", "Dial " + selected_dial["dial"], True, choices=hud_choices)
            self.content.publish_event("choice", "speed_dial_configure", "replace", choice_panel_content)
            return True
        return False

    def select_hud_phrases(self, selected_phrases = None):
        if selected_phrases != None:
            dial = None
            commands = []
            for selection in selected_phrases:
                commands.append(selection["phrase"])
                dial = selection["dial"]
            if dial is not None:
                self.speed_dial_manager.configure_dial(commands, dial)
            
            self.enable()
            return True
        return False    

def load_speed_dial_names():
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "speed_dial_config.csv")
    
    if not os.path.exists(config_file):
        speed_dial_header = "dialname;icon"
        speed_dial_defaults = [
            "one;dial_one.png",
            "two;dial_two.png",
            "three;dial_three.png",
            "four;dial_four.png",
            "five;dial_five.png",
            "six;dial_six.png",
            "seven;dial_seven.png",
            "eight;dial_eight.png",            
            "nine;dial_nine.png",                                                            
            "ten;dial_six.png",            
        ]
        file_contents = "" + speed_dial_header + "\n"
        file_contents += "\n".join(speed_dial_defaults)
        with open(config_file, "w") as f:
            f.write(file_contents)    
    
    speed_dials = {}
    with open(config_file, "r") as file:
        for index, line in enumerate(file.readlines()):
            if index == 0:
                continue
            split_vars = line.strip().split(";")
            if len(split_vars) > 1:
                speed_dial = {
                    "number": index,
                    "name": split_vars[0],
                    "icon": split_vars[1],
                    "commands": []
                }
                speed_dials[split_vars[0]] = speed_dial
    return speed_dials
    
speed_dial_manager = None
def start_speed_dial():
    global speed_dial
    speed_dial = SpeedDialManager(load_speed_dial_names())

app.register("ready", start_speed_dial)

@mod.action_class
class Actions:

    def speed_dial_activate(dial: str = None, type: str = 'voice'):
        """Activate the speed dial attached to this dial name"""
        global speed_dial
        speed_dial.activate_dial(dial, type)
        
    def speed_dial_clear(dial: str = None):
        """Clears the commands attached to a given speed dial"""
        global speed_dial
        speed_dial.configure_dial([], dial)
        
    def speed_dial_clear_everything():
        """Clears all available speed dials"""
        global speed_dial
        speed_dial.clear_dials()

    def speed_dial_last_commands(last_commands: int = 1, dial: str = None):
        """Sets the previous N commands as the activation for the selected dial"""
        global speed_dial
        speed_dial.configure_dial_last_commands(dial, last_commands)

    def speed_dial_next_commands(next_commands: int = 1, dial: str = None):
        """Sets the next N commands as the activation for the selected dial"""
        global speed_dial
        speed_dial.configure_dial_next_commands(dial, next_commands)
        
    def speed_dial_toggle_shortcuts(enabled: int = -1):
        """Enable or disable the usage of keyboard shortcuts to activate speed dials"""
        global speed_dial
        
        if enabled == -1:
            speed_dial.toggle_keyboard_shortcuts()
        else:
            speed_dial.toggle_keyboard_shortcuts(enabled > 0)
            
    def speed_dial_toggle_noises(enabled: int = -1):
        """Enable or disable the usage of noises to activate speed dials"""
        global speed_dial
        
        if enabled == -1:
            speed_dial.toggle_noises()
        else:
            speed_dial.toggle_noises(enabled > 0)

    def speed_dial_options():
        """Create the options menu available for the speed dial configuration"""
        global speed_dial
        speed_dial.open_hud_options_menu()
        
    def speed_dial_add_phrase(phrase: str):
        """Add a phrase directly to the speed dial stack"""
        global speed_dial
        speed_dial.force_add_phrase(phrase)