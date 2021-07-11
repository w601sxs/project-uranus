# Project-Uranus

![](https://img.shields.io/badge/Source-LiveATC-blue)
![](https://img.shields.io/badge/Dependencies-lxml-green)
![](https://img.shields.io/badge/Dependencies-ffmpeg-green)

## Abstract

This repo is design for discover and record all LiveATC streams, which sources from LiveATC. I am planning to use the recorded audio to do further analysis and train a aviation based speech recognition model.

## Requirement
To do this, you need to install the following package
- `python-ffmpeg`
- `lxml`
## Usage


## TODO
- Dispatch Large Scale Listener to (10 airports maybe)?
  - Need to isolate the output from each other, or we do docker run, not sure what's the plan yet
- Use database to manage the audio information
- Perhaps attach to a Cloud (AWS)?