from ovos_utils import classproperty
# from ovos_utils.log import LOG
from ovos_utils.process_utils import RuntimeRequirements
from ovos_workshop.intents import IntentBuilder
from ovos_workshop.decorators import intent_handler
# from ovos_workshop.intents import IntentHandler # Uncomment to use Adapt intents
from ovos_workshop.skills import OVOSSkill

import socket
import subprocess
import psutil

# Optional - if you want to populate settings.json with default values, do so here
DEFAULT_SETTINGS = {
    "future_setting1": True,
    "usage_threshold": 90,
    "net_testsite": "www.ibm.com",
    "log_level": "WARNING"
}


def network_up():

    try:
        socket.create_connection(('www.ibm.com', 80))
        return True
    except OSError:
        return False


def get_cpu_utilization():
    return psutil.cpu_percent(interval=1)


def get_disk_utilization():
    return psutil.disk_usage('/').percent


def get_memory_utilization():
    return psutil.virtual_memory().percent


def get_system_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = f.read().strip()
            return float(temp) / 1000.0  # Convert from millidegrees to degrees
    except Exception as e:
        print(f"Error getting system temperature: {e}")
        return None


def check_throttling():
    try:
        throttled_output = subprocess.check_output(['vcgencmd', 'get_throttled']).decode()
        if '0x0' in throttled_output:
            return False
        return True
    except Exception as e:
        print(f"Error checking throttling: {e}")
    return True


class HowAreThingsSkill(OVOSSkill):
    def __init__(self, *args, bus=None, **kwargs):
        """The __init__ method is called when the Skill is first constructed.
        Note that self.bus, self.skill_id, self.settings, and
        other base class settings are only available after the call to super().

        This is a good place to load and pre-process any data needed by your
        Skill, ideally after the super() call.
        """
        super().__init__(*args, bus=bus, **kwargs)
        self.learning = True

    def initialize(self):
        # merge default settings
        # self.settings is a jsondb, which extends the dict class and adds helpers like merge
        self.settings.merge(DEFAULT_SETTINGS, new_only=True)

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

    @property
    def my_setting(self):
        """Dynamically get the my_setting from the skill settings file.
        If it doesn't exist, return the default value.
        This will reflect live changes to settings.json files (local or from backend)
        """
        return self.settings.get("my_setting", "default_value")

    @property
    def log_level(self):
        """Dynamically get the 'log_level' value from the skill settings file.
        If it doesn't exist, return the default value.
        This will reflect live changes to settings.json files (local or from backend)
        """
        return self.settings.get("log_level", "INFO")

    @intent_handler("HowAreThings.intent")
    def handle_how_are_things_intent(self, message):
        """This is a Padatious intent handler.
        It is triggered using a list of sample phrases."""

        aok = True
        self.speak("I am checking a few things")
        if network_up():
            self.speak("Network looks good!")
        else:
            self.speak("I don't seem to have network connectivity")
            aok = False

        cpu_util = get_cpu_utilization()
        mem_util = get_memory_utilization()
        disk_util = get_disk_utilization()

        if cpu_util > 90 or mem_util > 90 or disk_util > 90:
            self.speak("System Utilization seems a tad high ...")
            aok = False

        self.speak("CPU Utilization is " + str(cpu_util) + " percent")
        self.speak("Memory Utilization is " + str(mem_util) + " percent")
        self.speak("Disk Utilization is " + str(disk_util) + " percent")

        current_temp = get_system_temperature()
        if get_system_temperature() > 70:
            self.speak("System Temperature seems a tad high")
            aok = False

        self.speak("System Temperature is " + str(current_temp) + " degrees Celsius")

        if check_throttling():
            self.speak("Throttling has occurred since last boot")
            aok = False
        else:
            self.speak("No sign of throttling, that's good!", wait=True)

        if aok:
            self.speak("I'm doing GREAT!", wait=True)
        else:
            self.speak("I've been better", wait=True)

    @intent_handler(IntentBuilder("RoboticsLawsIntent").require("LawKeyword").build())
    def handle_robotic_laws_intent(self, message):
        """This is an Adapt intent handler, but using a RegEx intent."""
        # Optionally, get the RegEx group from the intent message
        # law = str(message.data.get("LawOfRobotics", "all"))
        self.speak_dialog("robotics")

    def stop(self):
        """Optional action to take when "stop" is requested by the user.
        This method should return True if it stopped something or
        False (or None) otherwise.
        If not relevant to your skill, feel free to remove.
        """
        return
