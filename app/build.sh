#!/bin/bash

# Get the environment variables from .env file
set -a  
source .env
set +a

IMAGE_NAME=mips-compiler
CONTAINER_NAME=mips-compiler-prod

# Build the Docker image
echo "Building Docker image..."
DOCKER_BUILDKIT=0 docker build -t $IMAGE_NAME .

# Remove old container if it exists
if docker ps -a | grep -q $CONTAINER_NAME; then
    echo "Removing old container..."
    docker rm -f $CONTAINER_NAME
fi

# Run the container
echo "Running container..."
exec docker run -it -d -p $PORT:$PORT\
    --cap-add=SYS_ADMIN \
    --security-opt apparmor=unconfined \
    --security-opt seccomp=unconfined \
    --name $CONTAINER_NAME $IMAGE_NAME

