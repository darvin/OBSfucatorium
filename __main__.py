
from collections import namedtuple
from typing import NamedTuple
import subprocess
import toml
import time
import shlex
from flask import Flask, jsonify, request

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
    f"obs --collection {OBS_COLLECTION} --websocket_port {OBS_PORT} --websocket_password {OBS_PASSWORD} --startstreaming ", #--websocket_debug ",
  TermParams(title="sensors", command="glances --disable-plugin processlist,fs,diskio,network,now,processcount,ports -4 -1"),
  TermParams(title="top", command="gtop"),
  TermParams(title="glxgears-log", command="glxgears", font_string=FONT_STRING_LOG, geometry=TermGeometry(160, 50)),
  TermParams(title="df", command="watch -n 2 df", geometry=TermGeometry(20, 8)),
]

import threading

class Launcher:
    processes_launched = []

    _kill_timer = None

    @classmethod
    def kill(cls):
        if cls._kill_timer:
            cls._kill_timer.cancel()
            cls._kill_timer = None
        for p in cls.processes_launched:
            print(f"@KILLING {p}")
            p.kill()
        cls.processes_launched = []

    @classmethod
    def is_launched(cls):
        return len(cls.processes_launched) > 0
    
    @classmethod
    def keep_alive(cls):
        if cls._kill_timer:
            cls._kill_timer.cancel()
        cls._kill_timer = threading.Timer(5.0, cls.kill)
        cls._kill_timer.start()

    @classmethod
    def launch(cls):
        cls.kill()
        for cmd in LAUNCH_LIST:
            print(f"@LAUCHING\n{cmd}\n")
            if isinstance(cmd, TermParams):
                exec_name = "/bin/urxvt"
                argv = [cmd.title ] + shlex.split(str(cmd))
            else:
                exec_name = cmd.split(' ')[0]
                argv = cmd.split(' ')[1:]
            p = subprocess.Popen(argv, executable=exec_name)
            #, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            cls.processes_launched.append(p)

        cls.keep_alive()


    


app = Flask(__name__)


class SceneSwitcher():
    _obs_client = None
    scenes = []
    i = 0

    @classmethod
    def init_and_fetch_scenes(cls):
        cls._obs_client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD)
        resp = cls._obs_client.get_scene_list()
        cls.scenes = [di.get("sceneName") for di in reversed(resp.scenes)]
        print(f"######\n{SceneSwitcher.scenes}\n####")

    @classmethod
    def _update_scene(cls):
        cls._obs_client.set_current_program_scene(cls.current())


    @classmethod 
    def next(cls):
        if cls.i < len(cls.scenes)-1:
            cls.i += 1
        else:
            cls.i = 0
        cls._update_scene()
    
    @classmethod 
    def prev(cls):
        if cls.i > 0:
            cls.i -= 1
        else:
            cls.i = len(cls.scenes)-1
        cls._update_scene()


    @classmethod
    def switch(cls, name):
        cls.i = cls.scenes.index(name)
        cls._update_scene()


    @classmethod
    def current(cls):
        return cls.scenes[cls.i]

import logging
logging.basicConfig(level=logging.DEBUG)
obs_client = None

import obsws_python as obs

def main():
    app.run(debug=True, port=8888)
  


@app.route("/launch", methods=["GET"])
def launch():
    Launcher.launch()
    time.sleep(3)
    SceneSwitcher.init_and_fetch_scenes()
    return jsonify({"status": "launched"})

@app.route("/kill", methods=["GET"])
def kill():
    if Launcher.is_launched():
        Launcher.kill()
        return jsonify({"status": "killed"})
    else:
        return jsonify({"status": "already_killed"})


@app.route("/keepAlive", methods=["GET"])
def keep_alive():
    if not Launcher.is_launched():
        launch()
    Launcher.keep_alive()
    return jsonify({"status": "alive"})

@app.route("/scene/<scene_name>", methods=["GET"])
def scene(scene_name=None):
    if not Launcher.is_launched():
        launch()
    Launcher.keep_alive()
    if scene_name in SceneSwitcher.scenes:
        SceneSwitcher.switch(scene_name)
    elif scene_name == "next":
        SceneSwitcher.next()
    elif scene_name == "prev":
        SceneSwitcher.prev()
    new_scene = SceneSwitcher.current()
    return jsonify({"scene":new_scene})

import signal
import atexit


def handle_exit(*args):
    #fixme close obs client
    Launcher.kill()
    

if __name__ == "__main__":
    
    atexit.register(handle_exit)
    main()
    




