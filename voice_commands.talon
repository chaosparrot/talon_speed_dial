-
# Default speed dial
speed dial: user.speed_dial_activate()
speed dial last: user.speed_dial_last_commands()
speed dial last <number_small>: user.speed_dial_last_commands(number_small)
speed dial next: user.speed_dial_next_commands()
speed dial next <number_small>: user.speed_dial_next_commands(number_small)
speed dial clear: user.speed_dial_clear()

# Specific speed dials
speed dial {user.speed_dial_names}: user.speed_dial_activate(speed_dial_names)
speed dial {user.speed_dial_names} last: user.speed_dial_last_commands(1, speed_dial_names)
speed dial {user.speed_dial_names} last <number_small>: user.speed_dial_last_commands(number_small, speed_dial_names)
speed dial {user.speed_dial_names} next: user.speed_dial_next_commands(1, speed_dial_names)
speed dial {user.speed_dial_names} next <number_small>: user.speed_dial_next_commands(number_small, speed_dial_names)
speed dial {user.speed_dial_names} clear: user.speed_dial_clear(speed_dial_names)

# Clean up all the speed dials
speed dial clear everything: user.speed_dial_clear_everything()

# Add a phrase without activating it
^speed dial [add] phrase <phrase>$: user.speed_dial_add_phrase(phrase)

# Speed dial shortcuts toggle - Remove ### from bottom command to enable the toggle on the scroll lock button
speed dial shortcuts enable: user.speed_dial_toggle_shortcuts(1)
speed dial shortcuts disable: user.speed_dial_toggle_shortcuts(0)
###key(scroll_lock): user.speed_dial_toggle_shortcuts()

# Speed dial noise toggle
speed dial noise enable: 
    user.speed_dial_toggle_noises(1)
    user.speed_dial_toggle_pop(1)
speed dial noise disable: 
    user.speed_dial_toggle_noises(0)
    user.speed_dial_toggle_pop(0)