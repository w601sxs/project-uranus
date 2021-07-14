#!/bin/bash

# execute in repo root folder

# bash ./start_data_engines.sh

cd "./data_engine" \
&& docker-compose build \
&& docker-compose up