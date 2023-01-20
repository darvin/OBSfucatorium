
from collections import namedtuple
from typing import NamedTuple
import subprocess
import toml
import time
import shlex
import os
from flask import Flask, jsonify, request

ENV=dict(os.environ, DISPLAY=":0.0", XAUTHORITY=os.path.expanduser("~/.Xauthority"))
KEEP_ALIVE_TIMEOUT_SECONDS = 60.0
FONT_STRING_BLACKLETTER = "xft:F25 BlackletterTypewriter:pixelsize=20,xft:Fira Mono:pixelsize=24,xft:Bitstream Vera Sans Mono:pixelsize=33"
FONT_STRING_MONO = "xft:Fira Mono:pixelsize=24,xft:Bitstream Vera Sans Mono:pixelsize=33"
FONT_STRING_LOG = "xft:Fira Mono:pixelsize=10,xft:Bitstream Vera Sans Mono:pixelsize=33"
FONT_STRING_DEFAULT = FONT_STRING_MONO

class TermGeometry(NamedTuple):
    x: int = 88
    y: int = 25

    def __str__(self) -> str:
        return f"{self.x}x{self.y}"

class TermParams(NamedTuple):
    background_color: str = "magenta"
    foreground_color: str = "black"
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


import threading

AIRSIM_ENV_PATH = "/home/standard/src/AirSimEnvs/"

class Launcher:
    processes_launched = []

    _kill_timer = None

    _airsim_env = "hm"

    @classmethod
    def set_airsim_env(cls, name):
        envs = [ os.path.basename(f.path) for f in os.scandir(AIRSIM_ENV_PATH) if f.is_dir() ]
        if name in envs:
            self._airsim_env = name
            cls.full_relaunch()
            return name
        elif name == "next":
            i = envs.index(cls._airsim_env)
            i += 1
            if i == len(envs):
                i = 0
            cls._airsim_env = envs[i]
            cls.full_relaunch()
            return cls._airsim_env
        else:
            assert(0)


    @classmethod
    def launch_list(cls):
        return  [
f"obs --collection {OBS_COLLECTION} --websocket_port {OBS_PORT} --websocket_password {OBS_PASSWORD} --startstreaming ", #--websocket_debug ",
TermParams(title="simulator", command=f"./run_airsim.sh {AIRSIM_ENV_PATH}{cls._airsim_env}"),
TermParams(title="nvidia-smi", command="watch -n 3 nvidia-smi"),
  #TermParams(title="sensors", command="glances --disable-plugin processlist,fs,diskio,network,now,processcount,ports -4 -1"),
  #TermParams(title="top", command="gtop"),
  #TermParams(title="glxgears-log", command="glxgears", font_string=FONT_STRING_LOG, geometry=TermGeometry(160, 50)),
  #TermParams(title="df", command="watch -n 2 df", geometry=TermGeometry(20, 8)),
]

    @classmethod
    def kill_airsim(cls):
        subprocess.call(["./kill_airsim.sh"])

    @classmethod
    def kill(cls):
        if cls._kill_timer:
            cls._kill_timer.cancel()
            cls._kill_timer = None
        for p in cls.processes_launched:
            print(f"@KILLING {p}")
            p.kill()
        cls.kill_airsim()
        cls.processes_launched = []

    @classmethod
    def full_relaunch(cls):
        cls.kill()
        cls.launch()

    @classmethod
    def is_launched(cls):
        return len(cls.processes_launched) > 0

    @classmethod
    def keep_alive(cls):
        if cls._kill_timer:
            cls._kill_timer.cancel()
        cls._kill_timer = threading.Timer(KEEP_ALIVE_TIMEOUT_SECONDS, cls.kill)
        cls._kill_timer.start()

    @classmethod
    def launch(cls):
        cls.kill()
        for cmd in cls.launch_list():
            print(f"@LAUCHING\n{cmd}\n")
            if isinstance(cmd, TermParams):
                exec_name = "/bin/urxvt"
                argv = [cmd.title ] + shlex.split(str(cmd))
            else:
                exec_name = os.path.expanduser(cmd.split(' ')[0])
                argv = cmd.split(' ')[1:]
            p = subprocess.Popen(argv, executable=exec_name, env=ENV)
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
    app.run(debug=True, port=8001)
  


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


@app.route("/airsimEnv/<env_name>", methods=["GET"])
def airsim_env(env_name=None):
    if not Launcher.is_launched():
        launch()
    Launcher.keep_alive()
    return jsonify({"env":Launcher.set_airsim_env(env_name)})


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
    




