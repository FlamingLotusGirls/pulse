import time
import os
import sys
import effectlayer

class InputGetter:
    def update(self, effectparams):
        pass


# Crappy curses-based keyboard button emulator. See init method for key codes.
class KeyboardInputGetter(InputGetter):
    def __init__(self, screen):
        # curses stuff...
        import curses
        screen.nodelay(True) # make getch calls non-blocking
        self.screen = screen

        self.buttonDownKeys = ["d", "k"]
        self.buttonUpKeys = ["e", "i"]
        self.cachedTimes = [0, 0] # time that the button was pressed down or released

        for i in range(len(self.buttonDownKeys)):
            print("Button #%i down/up: %s/%s" % (i, self.buttonDownKeys[i], self.buttonUpKeys[i]))

    def update(self, effectparams):
            # get a character from the curses screen
            char = self.screen.getch()
            try:
                char = chr(char)
            except:
                pass

            for i in range(len(self.buttonDownKeys)):
                # update button-down times stored in this object
                if char == self.buttonDownKeys[i] and effectparams.buttonState[i] != True:
                    effectparams.buttonState[i] = True
                    self.cachedTimes[i] = time.time()
                elif char == self.buttonUpKeys[i] and effectparams.buttonState[i] != False:
                    effectparams.buttonState[i] = False
                    self.cachedTimes[i] = time.time()

                effectparams.buttonTimeSinceStateChange[i] = time.time() - self.cachedTimes[i]

# Button input getter checks to see if there's a node
# in /var/run/soma. If there is - its a sign of a button press.
# If node is not present - it means that the button
# is not pressed. It is assumed that there's another
# daemon process that runs in parallel to control the nodes
class ButtonInputGetter(InputGetter):
    #BUTTON_DEV_PATH = '/var/run/soma/button'
    BUTTON_DEV_PATH = '/tmp/button'
    button_id = ["A", "B"]

    class Button:
        dev_node = ""
        state = False
        time_changed = 0.0

    def __init__(self, button_count = 2):
        self.buttons = []
        for i in range(button_count):
            b = ButtonInputGetter.Button()
            b.dev_node = ButtonInputGetter.BUTTON_DEV_PATH + ButtonInputGetter.button_id[i]
            self.buttons.append(b)

    def update(self, effectparams):
        for i in range(len(self.buttons)):
            current_state = os.path.exists(self.buttons[i].dev_node)
            if (current_state != self.buttons[i].state):
                self.buttons[i].state = current_state
                self.buttons[i].time_changed = time.time()
                effectparams.buttonState[i] = current_state
            effectparams.buttonTimeSinceStateChange[i] = time.time() - self.buttons[i].time_changed

# Gets inputs from GPIO pins on Beaglebone Black
class GpioInputGetter(InputGetter):
    def __init__(self, gpios_list = (30,)):
        self.gpios_list = gpios_list
        self.button_previous_state = [False for gpio in gpios_list]
        self.button_on_set_time = [0.0 for gpio in gpios_list]
        gpio_export = open("/sys/class/gpio/export", "w")
        for gpio in gpios_list:
            gpio_export.write(str(gpio))
        gpio_export.close()

    def update(self, effectparams):
        if (not isinstance(effectparams, EffectParameters)):
            return
        if (not self.file):
            return

        for ix in range(0,len(self.gpios_list)):
            gpio = self.gpios_list[ix]
            filename = "/sys/class/gpio/gpio"+str(gpio)
            try:
                f = open(filename,"r")
                state = {'1': True, '0': False}[f.read()]
                f.close()
            except:
                continue
            effectparams.button_pressed_times[ix] = 0.0
            if (state):
                if (not self.button_previous_state):
                    self.button_on_set_time[ix] = time.time()
                else:
                    effectparams.button_pressed_times[ix] = time.time() - self.button_on_set_time[ix]
            self.button_previous_state = state
