# LiveATC Audio Fetcher

![](https://img.shields.io/badge/Source-LiveATC-blue)
![](https://img.shields.io/badge/Dependencies-lxml-green)
![](https://img.shields.io/badge/Dependencies-ffmpeg-green)

## Abstract

This repo is design for discover and record all LiveATC streams, which sources from LiveATC. I am planning to use the recorded audio to do further analysis and train a aviation based speech recognition model.

## Requirement
To do this, you need to install the following package
- `python-ffmpeg`

## Usage

### Record Raw Audio
Change parameter in `listener.py` and then run it to fetch the audio from this liveatc stream
```bash
python listener.py
```
### Convert Raw Audio to MP3
Change parameter in `converter.py` and then run it to convert the fetched raw audios in `listener.py` to the `.mp3` format
```bash
python converter.py
```