#!/usr/bin/env bash
docker build . --tag broken-machines
docker run --rm -d \
  -v "$(pwd)/rooms.yaml:/app/rooms.yaml:ro" \
  --name broken-machines \
  broken-machines
