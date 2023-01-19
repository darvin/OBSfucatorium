
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
        p = subprocess.Popen(argv, executable=exec_name)
           #, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes_launched.append(p)



    


app = Flask(__name__)
SCENES = []
SCENE_INDEX = 0


import logging
logging.basicConfig(level=logging.DEBUG)
import asyncio
import simpleobsws

parameters = simpleobsws.IdentificationParameters() # Create an IdentificationParameters object (optional for connecting)

ws = simpleobsws.WebSocketClient(url = f'ws://{OBS_HOST}:{OBS_PORT}') #, password = OBS_PASSWORD, identification_parameters = parameters) # Every possible argument has been passed, but none are required. See lib code for defaults.
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


async def ws_connect():
    await ws.connect() # Make the connection to obs-websocket
    await ws.wait_until_identified() # Wait for the identification handshake to complete


async def ws_disconnect():
    await ws.disconnect()

async def ws_get_scene_list():
    request = simpleobsws.Request('GetVersion') # Build a Request object

    ret = await ws.call(request) # Perform the request
    if ret.ok(): # Check if the request succeeded
        print("Request succeeded! Response data: {}".format(ret.responseData))
    return ret

async def fetch_scenes():
    await ws_connect()
    SCENES = await ws_get_scene_list()
    print(SCENES)
    await ws_disconnect()


def main():
    # launch_commands()
    #time.sleep(1000)
    #loop.run_until_complete(ws_connect())
    #SCENES = loop.run_until_complete(ws_get_scene_list())
    app.run(debug=True, port=8888)
    
    # obs_client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD)
    # resp = obs_client.get_scene_list()
    # SCENES = [di.get("sceneName") for di in reversed(resp.scenes)]
    # for scene in scenes:
    #     print(f"Switching to scene {scene}")
    #     obs_client.set_current_program_scene(scene)
    #     time.sleep(0.5)





@app.route("/keepAlive", methods=["GET"])
def keep_alive():
    return jsonify({"status": "alive"})

@app.route("/scene/<scene_name>", methods=["GET"])
def scene(scene_name=None):
    if not SCENES:
        loop.run_until_complete(fetch_scenes())
    if scene_name in SCENES:
        SCENE_INDEX = SCENES.index(scene_name)
    elif scene_name == "next":
        if SCENE_INDEX < len(SCENES):
            SCENE_INDEX += 1
        else:
            SCENE_INDEX = 0
    elif scene_name == "prev":
        if SCENE_INDEX > 0:
            SCENE_INDEX -= 1
        else:
            SCENE_INDEX = len(SCENES)
    new_scene = SCENES[SCENE_INDEX]
    return jsonify({"scene":new_scene})

import signal
import atexit


def handle_exit(*args):
    loop.run_until_complete(ws_disconnect())
    kill_commands()
    

if __name__ == "__main__":
    
    atexit.register(handle_exit)
    main()
    




