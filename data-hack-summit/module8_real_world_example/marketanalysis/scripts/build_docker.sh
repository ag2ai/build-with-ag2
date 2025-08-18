#!/bin/bash

echo -e "\033[0;32mBuilding fastagency docker image for linux/amd64 and pushing to registry\033[0m"

# Ensure buildx is set up
docker buildx create --use 2>/dev/null

# Build and push for linux/amd64
docker buildx build --platform linux/amd64 -t marketanalysisacr.azurecr.io/marketanalysis:latest -f docker/Dockerfile . --push

echo -e "\033[0;32mSuccessfully built and pushed fastagency docker image for linux/amd64\033[0m"
