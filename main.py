import time, digitalio
from machine import Pin, I2C, PWM
from machine_i2c_lcd import I2cLcd
from keypad import Matrix_Keypad
from settings import Settings

led = Pin(18, Pin.OUT)
buzzer = PWM(Pin(19))
buzzer.freq(1000)

lcd = I2cLcd(I2C(0, scl=Pin(17), sda=Pin(16), freq=400000), 0x27, 2, 16)

keypad = Matrix_Keypad(
    [digitalio.DigitalInOut(x) for x in (Pin(14), Pin(9), Pin(10), Pin(12))],
    [digitalio.DigitalInOut(x) for x in (Pin(13), Pin(15), Pin(11))],
    ((1, 2, 3), (4, 5, 6), (7, 8, 9), ("*", 0, "#")))

class Screen:
    def __init__(self, led, buzzer, lcd, keypad, settings):
        '''
        * -1 = settings
        * 0 = enter code to plant the bomb
        * 1 = wrong code
        * 2 = switch code to stars and play bomb planted sound
        * 3 = wait for defuse while flashing LED and countdown
        * 4 = bomb has been defused
        * 5 = bomb go boom
        '''
        self.mode = 0
        
        self.led = led
        self.buzzer = buzzer
        self.lcd = lcd
        self.keypad = keypad
        
        self.last_keys = []
        self.code = ""
        self.last_code = ""
        
        self.timer = 0
        self.wrong_timer = 0
        
        self.open_settings = 0
        self.settings = settings
        self.bomb_code = self.settings.json['code']
        self.bomb_timer = self.settings.json['timer']
        self.selected_setting = 0
        self.changing_setting = False
        
        self.change_mode(0)
        
    def change_mode(self, new_mode):
        self.mode = new_mode
        self.code = ""
        self.last_code = ""
        if self.mode == -1:
            self.lcd.clear()
            self.lcd.move_to(0, 0)
            self.lcd.putstr(">timer      " + str(self.bomb_timer))
            self.lcd.move_to(0, 1)
            self.lcd.putstr(" code    " + self.bomb_code)
        if self.mode == 0:
            self.settings.load_settings()
            self.bomb_code = self.settings.json['code']
            self.bomb_timer = self.settings.json['timer']
            self.led.off()
            self.buzzer.duty_u16(0)
            self.lcd.clear()
            self.lcd.move_to(6, 0)
            self.lcd.putstr("Enter Code")
        if self.mode == 1:
            self.timer = 20
            self.lcd.clear()
            self.lcd.move_to(6, 0)
            self.lcd.putstr("WRONG CODE")
            self.lcd.move_to(9, 1)
            self.lcd.putstr("*******")
        if self.mode == 2:
            self.timer = self.bomb_timer * 10
            self.lcd.clear()
            self.lcd.move_to(4, 0)
            self.lcd.putstr("Bomb Planted")
            self.lcd.move_to(0, 1)
            # self.lcd.putstr(str(self.bomb_timer) + "       *******")
            self.lcd.putstr(self.get_bomb_timer(self.bomb_timer))
        if self.mode == 4:
            self.led.off()
            self.buzzer.duty_u16(0)
            self.lcd.clear()
            self.lcd.move_to(2, 0)
            self.lcd.putstr("Bomb Defused")
            self.lcd.move_to(0, 1)
            if (self.timer < 600):
                self.lcd.putstr("with {message:0<4}s left.".format(message = str(self.timer / 10)))
            else:
                self.lcd.putstr("with {message:0<4} left.".format(message = self.get_bomb_timer(self.timer / 10)))
            self.timer = 50
        if self.mode == 5:
            self.timer = 30
            self.lcd.clear()
            self.lcd.move_to(6, 1)
            self.lcd.putstr("BOOM")
            
    def get_bomb_timer(self, time):
        if time >= 60:
            minutes = int(time / 60)
            seconds = int(time % 60)
            if seconds < 10: 
                return str(minutes) + ":0" + str(seconds)
            else:
                return str(minutes) + ":" + str(seconds)
        elif time < 10:
            return "0" + str(time)[:-2] + "  "
        else:
            return str(time)[:-2] + "  "
            
            
    def update(self):
        keys = self.keypad.pressed_keys
        if keys:
            for key in keys:
                in_last = False
                for last_key in self.last_keys:
                    if key == last_key:
                        in_last = True
                        continue
                if in_last == False:
                    self.last_keys.append(key)
                    if key == "*":
                        if self.mode == -1 and not self.changing_setting:
                            if self.selected_setting == 0:
                                self.selected_setting = 1
                                self.lcd.move_to(0, 0)
                                self.lcd.putstr(" ")
                                self.lcd.move_to(0, 1)
                                self.lcd.putstr(">")
                            else:
                                self.selected_setting = 0
                                self.lcd.move_to(0, 0)
                                self.lcd.putstr(">")
                                self.lcd.move_to(0, 1)
                                self.lcd.putstr(" ")
                        else:
                            self.code = self.code[:-1]
                    elif key == "#":
                        if self.mode == -1:
                            self.changing_setting = True
                            if self.selected_setting == 0:
                                self.lcd.move_to(0, 0)
                                self.lcd.putstr("-")
                                self.lcd.move_to(12, 0)
                                self.lcd.putstr("|   ")
                                self.lcd.move_to(12, 0)
                            else:
                                self.lcd.move_to(0, 1)
                                self.lcd.putstr("-")
                                self.lcd.move_to(9, 1)
                                self.lcd.putstr("|      ")
                                self.lcd.move_to(9, 1)
                        else:
                            self.code = ""
                    else:
                        self.open_settings = 0
                        self.code += str(key)
        else:
            self.last_keys = []
            
        if self.mode == -1:
            if self.last_keys != []:
                if self.changing_setting:
                    if self.selected_setting == 0:
                        self.lcd.move_to(12, 0)
                        self.lcd.putstr(self.code)
                        if len(self.code) == 4:
                            self.settings.json['timer'] = int(self.code)
                            self.code = ""
                            self.lcd.move_to(0, 0)
                            self.lcd.putstr(">")
                            self.changing_setting = False
                            self.settings.save_settings()
                    else:
                        self.lcd.move_to(9, 1)
                        self.lcd.putstr(self.code)
                        if len(self.code) == 7:
                            self.settings.json['code'] = self.code
                            self.code = ""
                            self.lcd.move_to(0, 1)
                            self.lcd.putstr(">")
                            self.changing_setting = False
                            self.settings.save_settings()
                else:
                    if "*" in self.last_keys:
                        self.open_settings += 1
                        if self.open_settings == 10:
                            self.change_mode(0)
                            self.open_settings = 0
            else:
                self.open_settings = 0
            
        
        # update LCD and check code
        if self.mode == 0:
            if self.last_keys != []:
                self.lcd.clear()
                self.lcd.move_to(6, 0)
                self.lcd.putstr("Enter Code")
                self.lcd.move_to(16 - len(self.code), 1)
                self.lcd.putstr(self.code)
                if len(self.code) == 7:
                    if self.code == self.bomb_code:
                        self.change_mode(2)
                    else:
                        self.change_mode(1)
                if "#" in self.last_keys:
                    self.open_settings += 1
                    if self.open_settings == 10:
                        self.change_mode(-1)
                        self.open_settings = 0
            else:
                self.open_settings = 0
                        
        if self.mode == 1:
            if self.timer > 0:
                self.timer -= 1
                if self.timer % 5 < 3:
                    self.lcd.move_to(6, 0)
                    self.lcd.putstr("WRONG CODE")
                    self.lcd.move_to(9, 1)
                    self.lcd.putstr("*******")
                else:
                    self.lcd.clear()
            else:
                self.change_mode(0)
                    
        if self.mode == 2:
            if self.timer > 0:
                self.timer -= 1
                # led control
                if self.timer > 100:
                    if self.timer % 10 == 0:
                        self.led.toggle()
                        self.buzzer.duty_u16(1000)
                    else:
                        self.buzzer.duty_u16(0)
                elif self.timer > 50:
                    if self.timer % 5 == 0:
                        self.led.toggle()
                        self.buzzer.duty_u16(1000)
                    else:
                        self.buzzer.duty_u16(0)
                elif self.timer % 2 == 0:
                    self.led.toggle()
                    self.buzzer.duty_u16(1000)
                else:
                    self.buzzer.duty_u16(0)
                
                # lcd control
                if self.timer % 10 == 0:
                    self.lcd.move_to(0, 1)
                    self.lcd.putstr(self.get_bomb_timer(self.timer / 10))
                if self.last_keys != []:
                    self.lcd.move_to(9, 1)
                    self.lcd.putstr("{message:*<7}".format(message = self.code))
                    if len(self.code) == 7:
                        if self.code == self.bomb_code:
                            self.change_mode(4)
                        else:
                            #self.change_mode(5)
                            self.lcd.move_to(4, 0)
                            self.lcd.putstr(" WRONG CODE!")
                            self.code = ""
                            self.wrong_timer = 20
                if self.wrong_timer > 0:
                    self.wrong_timer -= 1
                    if self.wrong_timer % 5 < 3:
                        self.lcd.move_to(4, 0)
                        self.lcd.putstr("            ")
                    else:
                        self.lcd.move_to(4, 0)
                        self.lcd.putstr(" WRONG CODE!")
                if self.wrong_timer == 0:
                    self.lcd.move_to(4, 0)
                    self.lcd.putstr("Bomb Planted")
                    self.lcd.move_to(9, 1)
                    self.lcd.putstr("*******")
                    self.wrong_timer = -1
            else:
                self.change_mode(5)
                
        #if self.mode == 4:
            #if self.timer > 0:
                #self.timer -= 1
            #else:
                #self.change_mode(0)
                
        if self.mode == 5:
            if self.timer > 0:
                self.led.on()
                self.timer -= 1
                if self.timer == 25:
                    self.lcd.move_to(0, 0)
                    self.lcd.putstr("       _  -     \n     _")
                    self.lcd.move_to(10, 1)
                    self.lcd.putstr(" -    ")
                if self.timer == 20:
                    self.lcd.move_to(0, 0)
                    self.lcd.putstr("     - *   **   \n  * - ")
                    self.lcd.move_to(10, 1)
                    self.lcd.putstr("  -_  ")
                if self.timer == 15:
                    self.lcd.move_to(0, 0)
                    self.lcd.putstr("*  -** *   _+# *\n * -  ")
                    self.lcd.move_to(10, 1)
                    self.lcd.putstr("   #*-")
                if self.timer == 10:
                    self.lcd.move_to(0, 0)
                    self.lcd.putstr("*  *- *     _+**\n#     ")
                    self.lcd.move_to(10, 1)
                    self.lcd.putstr("    #*")
                if self.timer ==  5:
                    self.lcd.move_to(0, 0)
                    self.lcd.putstr("* *  *       _+*\n      ")
                    self.lcd.move_to(10, 1)
                    self.lcd.putstr("     #")
            else:
                # self.led.off()
                # self.change_mode(0)
                # keep boom up
                self.timer = 25
                

settings = Settings()
screen = Screen(led, buzzer, lcd, keypad, settings)

while True:
    screen.update()
    time.sleep(0.1)
    
