#!/bin/bash

CONTAINER_NAME="pangea-litellm-container"

docker kill "$CONTAINER_NAME"
docker container rm "$CONTAINER_NAME"

docker run -d -it -p 4000:4000 -p 8011:8001 -p 8012:8002 \
  -e PANGEA_AI_GUARD_TOKEN="$PANGEA_AI_GUARD_TOKEN" \
  --name "$CONTAINER_NAME" litellm_plugin