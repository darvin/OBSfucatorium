#!/bin/bash -e

	 ID=$(docker ps | grep "airsim" | cut -d" " -f1)
 	echo $ID
	docker container stop "${ID}"
#docker container rm "${ID}"


