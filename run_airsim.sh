#!/bin/bash -e


cd ~/src/AirSim/docker

./run_airsim_image_binary.sh airsim_source:4.27.2-opengl-ubuntu18.04 $1/LinuxNoEditor/RUN.sh


