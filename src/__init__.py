from ovos_utils import classproperty
from ovos_utils.log import LOG
from ovos_utils.process_utils import RuntimeRequirements
# from ovos_workshop.intents import IntentBuilder
from ovos_workshop.decorators import intent_handler
# from ovos_workshop.intents import IntentHandler # Uncomment to use Adapt intents
from ovos_workshop.skills import OVOSSkill

import socket
import subprocess
import psutil

from .version import (
    VERSION_MAJOR,
    VERSION_MINOR,
    VERSION_BUILD,
    VERSION_ALPHA,
    VERSION_TAG
)

DEFAULT_SETTINGS = {
            "my_name": "Papa",
            "usage_threshold": 90,
            "net_testsite": "www.ibm.com",
            "log_level": "DEBUG"
        }

class HowAreThingsSkill(OVOSSkill):
    def __init__(self, *args, **kwargs):
        """Construct the skill. Settings are (re)loaded again in initialize()
        after the defaults have been merged into the settings file.
        """
        super().__init__(*args, **kwargs)
        self._load_settings()

    def _load_settings(self):
        """Load settings into attributes, falling back to DEFAULT_SETTINGS."""
        self.my_name = self.settings.get("my_name", DEFAULT_SETTINGS["my_name"])
        self.usage_threshold = self.settings.get("usage_threshold", DEFAULT_SETTINGS["usage_threshold"])
        self.net_testsite = self.settings.get("net_testsite", DEFAULT_SETTINGS["net_testsite"])
        self.log_level = self.settings.get("log_level", DEFAULT_SETTINGS["log_level"])

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

    @staticmethod
    def skill_version():
        version_string = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_BUILD}"
        if VERSION_ALPHA and int(VERSION_ALPHA) > 0:
            version_string += f"a{VERSION_ALPHA}"
        return version_string

    def initialize(self):
        LOG.debug("initialize() called")

        # self.settings is a jsondb, which extends dict and adds helpers like merge.
        # new_only=True never overwrites values already stored in settings.json.
        self.settings.merge(DEFAULT_SETTINGS, new_only=True)
        self._load_settings()

        # Announce version and tag only when skill-level debug is on
        if self.log_level.upper() == "DEBUG":
            self._announce_version()

    def _announce_version(self):
        spoken_version = self.skill_version().replace(".", " point ").replace("a", " alpha ")
        self.speak(
            f"How are things skill, version {spoken_version}, {VERSION_TAG}, initialized",
            wait=False
        )

    def network_up(self):
        try:
            # timeout so a dead network can't hang the handler; "with" closes the socket
            with socket.create_connection((self.net_testsite, 80), timeout=3):
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
                return float(temp) / 1000.0  # milli-degrees to degrees
        except Exception as e:
            LOG.warning(f"Error getting system temperature: {e}")
            return None

    @classmethod
    def check_throttling(cls):
        """Return (throttled_now, throttled_since_boot), or None if it can't be read."""
        try:
            throttled_output = subprocess.check_output(['vcgencmd', 'get_throttled']).decode().strip()
            throttled_value = int(throttled_output.split('=')[1], 16)

            # Bits 0-2: under-voltage / freq capped / throttled, right now
            throttled_now = bool(throttled_value & 0b111)
            # Bits 16-18: the same three conditions, have occurred since boot
            throttled_since_boot = bool((throttled_value >> 16) & 0b111)

            return throttled_now, throttled_since_boot

        except Exception as e:
            LOG.warning(f"Error checking throttling: {e}")
            return None

    def _speak(self, utterance, wait=False, expect_response=False):
        """Wrapper around self.speak that also logs to skill log at DEBUG level."""
        if self.log_level.upper() == "DEBUG":
            LOG.debug(f"[HowAreThings SPEAK] {utterance}")
        self.speak(utterance, wait=wait, expect_response=expect_response)

    @intent_handler("HowAreThings.intent")
    def handle_how_are_things_intent(self):
        """This is a Padatious intent handler.
        It is triggered using a list of sample phrases."""

        aok = True
        self._speak("I am checking a few things")
        if self.network_up():
            self._speak("Network looks good!")
        else:
            self._speak("I don't seem to have network connectivity")
            aok = False

        cpu_util = self.get_cpu_utilization()
        mem_util = self.get_memory_utilization()
        disk_util = self.get_disk_utilization()

        if cpu_util > self.usage_threshold or mem_util > self.usage_threshold or disk_util > self.usage_threshold:
            self._speak("System Utilization seems a tad high ...")
            aok = False

        self._speak("CPU Utilization is " + str(round(cpu_util)) + " percent")
        self._speak("Memory Utilization is " + str(round(mem_util)) + " percent")
        self._speak("Disk Utilization is " + str(round(disk_util)) + " percent")

        current_temp = self.get_system_temperature()
        if current_temp is not None and current_temp > 70:
            self._speak("System Temperature seems a tad high")
            aok = False

        if current_temp is not None:
            self._speak("System Temperature is " + str(round(current_temp)) + " degrees Celsius")
        else:
            self._speak("I couldn't read the system temperature")

        throttle = self.check_throttling()
        if throttle is None:
            self._speak("I couldn't check for throttling")
        else:
            throttled_now, throttled_since_boot = throttle
            if throttled_now:
                self._speak("The system is being throttled right now")
                aok = False
            elif throttled_since_boot:
                self._speak("Throttling has occurred since last boot")
                aok = False
            else:
                self._speak("No sign of throttling, that's good!")

        if aok:
            self._speak("I'm doing GREAT!", wait=True)
        else:
            self._speak("I've been better", wait=True)

    @intent_handler("WhatAreYouDoing.intent")
    def handle_what_are_you_doing_intent(self, _message):
        """Handle WhatAreYouDoing.intent and respond with random phrases """
        # From WhatAreYouDoing.dialog
        self.speak_dialog("WhatAreYouDoing", {"name": self.my_name})

    @intent_handler("AreYouThere.intent")
    def handle_are_you_there_intent(self, _message):
        """Handle AreYouThere.intent and respond with random phrases """
        # From AreYouThere.dialog
        self.speak_dialog("AreYouThere", {"name": self.my_name})

    @intent_handler("WhoDaMan.intent")
    def handle_who_da_man_intent(self, _message):
        """Handle WhoDaMan.intent and respond with random phrases """
        # From WhoDaMan.dialog
        self.speak_dialog("WhoDaMan", {"name": self.my_name})

    def stop(self):
        """Optional action to take when "stop" is requested by the user.
        This method should return True if it stopped something or
        False (or None) otherwise.
        If not relevant to your skill, feel free to remove.
        """
        return
