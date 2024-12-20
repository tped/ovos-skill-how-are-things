from ovos_utils import classproperty
# from ovos_utils.log import LOG
from ovos_utils.process_utils import RuntimeRequirements
# from ovos_workshop.intents import IntentBuilder
from ovos_workshop.decorators import intent_handler
# from ovos_workshop.intents import IntentHandler # Uncomment to use Adapt intents
from ovos_workshop.skills import OVOSSkill

import socket
import subprocess
import psutil

DEFAULT_SETTINGS = {
            "my_name": "Papa",
            "usage_threshold": 90,
            "net_testsite": "www.ibm.com",
            "log_level": "WARNING"
        }


class HowAreThingsSkill(OVOSSkill):
    def __init__(self, *args, bus=None, **kwargs):
        """The __init__ method is called when the Skill is first constructed.
        This is a good place to load and pre-process any data needed by your
        Skill, ideally after the super() call.
        """
        super().__init__(*args, bus=bus, **kwargs)
        self.learning = True

        # Load settings into variables, using defaults if no setting is found
        self.my_name = self.settings.get("my_name", "default_name")
        self.usage_threshold = self.settings.get("usage_threshold", 90)
        self.net_testsite = self.settings.get("net_testsite", "www.ibm.com")
        self.log_level = self.settings.get("log_level", "INFO")

    @classproperty
    def runtime_requirements(self):
        return RuntimeRequirements(
            internet_before_load=False,
            network_before_load=False,
            gui_before_load=False,
            requires_internet=False,
            requires_network=False,
            requires_gui=False,
            no_internet_fallback=True,
            no_network_fallback=True,
            no_gui_fallback=True,
        )

    def initialize(self):
        """This Method is called when the Skill is fully initialized."""
        # Optional - if you want to populate settings.json with default values, do so here

        # Merge default settings
        # self.settings is a jsondb, which extends the dict class and adds helpers like merge
        self.settings.merge(DEFAULT_SETTINGS, new_only=True)

        # Define and register Adapt intent IF/WHEN we want to use Adapt
        # what_are_you_doing_intent = IntentBuilder("WhatAreYouDoingIntent") \
        #     .require("WhatKeyword") \
        #     .optionally("DoingKeyword") \
        #     .build()
        # self.register_intent(what_are_you_doing_intent, self.handle_what_are_you_doing_intent)

    def network_up(self):
        try:
            socket.create_connection((self.net_testsite, 80))
            return True
        except OSError:
            return False

    @classmethod
    def get_cpu_utilization(cls):
        return psutil.cpu_percent(interval=1)

    @classmethod
    def get_disk_utilization(cls):

        return psutil.disk_usage('/').percent

    @classmethod
    def get_memory_utilization(cls):
        return psutil.virtual_memory().percent

    @classmethod
    def get_system_temperature(cls):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = f.read().strip()
                return float(temp) / 1000.0  # Convert from millidegrees to degrees
        except Exception as e:
            print(f"Error getting system temperature: {e}")
            return None

    @classmethod
    def check_throttling(cls):
        try:
            throttled_output = subprocess.check_output(['vcgencmd', 'get_throttled']).decode()
            if '0x0' in throttled_output:
                return False
            return True
        except Exception as e:
            print(f"Error checking throttling: {e}")
        return True

    @intent_handler("HowAreThings.intent")
    def handle_how_are_things_intent(self, message):
        """This is a Padatious intent handler.
        It is triggered using a list of sample phrases."""

        aok = True
        self.speak("I am checking a few things")
        if self.network_up():
            self.speak("Network looks good!")
        else:
            self.speak("I don't seem to have network connectivity")
            aok = False

        cpu_util = self.get_cpu_utilization()
        mem_util = self.get_memory_utilization()
        disk_util = self.get_disk_utilization()

        if cpu_util > self.usage_threshold or mem_util > self.usage_threshold or disk_util > self.usage_threshold:
            self.speak("System Utilization seems a tad high ...")
            aok = False

        self.speak("CPU Utilization is " + str(cpu_util) + " percent")
        self.speak("Memory Utilization is " + str(mem_util) + " percent")
        self.speak("Disk Utilization is " + str(disk_util) + " percent")

        current_temp = self.get_system_temperature()
        if self.get_system_temperature() > 70:
            self.speak("System Temperature seems a tad high")
            aok = False

        self.speak("System Temperature is " + str(current_temp) + " degrees Celsius")

        if self.check_throttling():
            self.speak("Throttling has occurred since last boot")
            aok = False
        else:
            self.speak("No sign of throttling, that's good!", wait=True)

        if aok:
            self.speak("I'm doing GREAT!", wait=True)
        else:
            self.speak("I've been better", wait=True)

    @intent_handler("WhatAreYouDoing.intent")
    def handle_what_are_you_doing_intent(self, message):
        """Handle WhatAreYouDoing.intent and respond with random phrases """
        # From WhatAreYouDoing.dialog
        self.speak_dialog("WhatAreYouDoing", {"name": self.my_name})

    @intent_handler("WhoDaMan.intent")
    def handle_who_da_man_intent(self, message):
        """Handle WhoDaMan.intent and respond with random phrases """
        # From WhatAreYouDoing.dialog
        self.speak_dialog("WhoDaMan", {"name": self.my_name})

    def stop(self):
        """Optional action to take when "stop" is requested by the user.
        This method should return True if it stopped something or
        False (or None) otherwise.
        If not relevant to your skill, feel free to remove.
        """
        return
