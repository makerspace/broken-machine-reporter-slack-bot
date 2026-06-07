#!/usr/bin/env bash
docker build . --tag broken-machines
docker run --rm -d broken-machines
