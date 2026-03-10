#!/bin/bash

TARGET_DIR=/docker/llama-farm
echo "Deploying containers to remote"

echo "Current working directory: $(pwd)"

echo "Copying files..."
echo "======================"
scp ./compose.yaml "gmferland@polecat:${TARGET_DIR}"

echo ""
echo "Launching remote shell..."
ssh gmferland@polecat.lan "$(cat << EOF
set -e
cd "${TARGET_DIR}"
echo "Working directory: \$(pwd)"
echo "Currently running containers..."
docker ps

echo ""
echo "Rebuilding containers..."
docker compose up --build --detach --remove-orphans

echo "Successfully deployed containers"
docker ps
EOF)"
