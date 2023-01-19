
from collections import namedtuple
from typing import NamedTuple
import subprocess
import toml
import time
import shlex
import obsws_python as obs

FONT_STRING_BLACKLETTER = "xft:F25 BlackletterTypewriter:pixelsize=20,xft:Pragmata Pro Mono:pixelsize=24,xft:Bitstream Vera Sans Mono:pixelsize=33"
FONT_STRING_MONO = "xft:Pragmata Pro Mono:pixelsize=24,xft:Bitstream Vera Sans Mono:pixelsize=33"
FONT_STRING_LOG = "xft:Pragmata Pro Mono:pixelsize=10,xft:Bitstream Vera Sans Mono:pixelsize=33"
FONT_STRING_DEFAULT = FONT_STRING_BLACKLETTER

class TermGeometry(NamedTuple):
    x: int = 88
    y: int = 25

    def __str__(self) -> str:
        return f"{self.x}x{self.y}"

class TermParams(NamedTuple):
    background_color: str = "magenta"
    foreground_color: str = "white"
    font_string: str = FONT_STRING_DEFAULT
    geometry: TermGeometry = TermGeometry()
    title: str = "-NoTitle- Shell"
    command: str = "sh"

    def __str__(self) -> str:
        return f"-bg {self.background_color} -fg {self.foreground_color} -fn \"{self.font_string}\" -bl +sb    -geometry {self.geometry}  -T {self.title}   -e {self.command}"



with open("config.toml") as config_file:
    config = toml.load(config_file)

OBS_HOST = config["connection"]["host"]
OBS_PORT = config["connection"]["port"]
OBS_PASSWORD = config["connection"]["password"]
OBS_COLLECTION = "GLXGEARS"


LAUNCH_LIST = [
    f"obs --collection {OBS_COLLECTION} --websocket_debug --websocket_port {OBS_PORT} --websocket_password {OBS_PASSWORD} --startstreaming ",
  TermParams(title="sensors", command="glances --disable-plugin processlist,fs,diskio,network,now,processcount,ports -4 -1"),
  TermParams(title="top", command="gtop"),
  TermParams(title="glxgears-log", command="glxgears", font_string=FONT_STRING_LOG, geometry=TermGeometry(160, 50)),
  TermParams(title="df", command="watch -n 2 df", geometry=TermGeometry(20, 8)),
]


processes_launched = []

def kill_commands():
    for p in processes_launched:
        print(f"@KILLING {p}")
        p.kill()

def launch_commands():
    kill_commands()
    for cmd in LAUNCH_LIST:
        print(f"@LAUCHING\n{cmd}\n")
        if isinstance(cmd, TermParams):
            exec_name = "/bin/urxvt"
            argv = [cmd.title ] + shlex.split(str(cmd))
        else:
            exec_name = cmd.split(' ')[0]
            argv = cmd.split(' ')[1:]
        p = subprocess.Popen(argv, executable=exec_name, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes_launched.append(p)




def main():
    launch_commands()
    time.sleep(1000)
    with obs.ReqClient() as client:
        resp = client.get_scene_list()
        scenes = [di.get("sceneName") for di in reversed(resp.scenes)]

        for scene in scenes:
            print(f"Switching to scene {scene}")
            client.set_current_program_scene(scene)
            time.sleep(0.5)



import signal
import atexit


def handle_exit(*args):
    kill_commands()

if __name__ == "__main__":
    
    atexit.register(handle_exit)
    main()
    




