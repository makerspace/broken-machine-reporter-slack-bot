#!/usr/bin/env bash
docker run -it \
  -v $(pwd):/app \
  broken-machines \
  python setup.py
