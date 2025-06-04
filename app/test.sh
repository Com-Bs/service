#!/bin/bash

# Get the environment variables from .env file
set -a  
source .env
set +a

IMAGE_NAME=mips-compiler
CONTAINER_NAME=mips-compiler-test

# Build the Docker image
echo "Building Docker image..."
docker build -t $IMAGE_NAME .

# Remove old container if it exists
if docker ps -a | grep -q $CONTAINER_NAME; then
    echo "Removing old container..."
    docker rm -f $CONTAINER_NAME
fi

# Run the tests
echo "Running tests..."
docker run --rm \
    --cap-add=SYS_ADMIN \
    --security-opt apparmor=unconfined \
    --security-opt seccomp=unconfined \
    --name $CONTAINER_NAME $IMAGE_NAME \
    pytest

# Capture exit code
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Some tests failed."
fi

exit $TEST_EXIT_CODE