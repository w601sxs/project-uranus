# LiveATC Audio Fetcher

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

### Record Raw Audio
Change parameter in `listener.py` and then run it to fetch the audio from this liveatc stream
- you are expected to see the scripts starts to write stream to stdout, if there is someone talking, log will pops up saying this frame will be concatenate with other frames and save to a raw file. Size of the raw file is totally depends on how long the conversation lasts
```bash
python listener.py
```
### Convert Raw Audio to MP3
Change parameter in `converter.py` and then run it to convert the fetched raw audios in `listener.py` to the `.mp3` format
- you are expected to see the script monitoring the raw_audio_dir and convert all the raw file to mp3 and store in clean_audio_dir
- not sure why the overwrite issue comes up yet, and if there is automate solution
```bash
python converter.py
```

### Fetch the latest streaming list
Simply do the run the following script
- you are expected to see a csv named stream_info.csv comes out to your repo folder, examples data is something like the following table
```bash
python stream_finder.py
```

<!-- example table -->
|flag               |stream_link                             |abstract                          |category  |metar                                                                               |location                             |fetch-time             |
|-------------------|----------------------------------------|----------------------------------|----------|------------------------------------------------------------------------------------|-------------------------------------|-----------------------|
|kdfw1_app_124300   |http://d.liveatc.net/kdfw1_app_124300   |KDAL App/Dep (East Side North Low)|US-Class-B|KDFW 311953Z 12005KT 10SM OVC085 23/20 A3004 RMK AO2 LTG DSNT SW SLP167 T02330200   |Dallas, Texas, United States         |2021-05-31 20:15:13 UTC|
|kdaa2_twr          |http://d.liveatc.net/kdaa2_twr          |KDAA/KADW Tower                   |US-Class-B|KDAA 311956Z AUTO 02004KT 10SM CLR 24/08 A3025 RMK AO2 SLP246 T02360084 $           |Camp Springs, Maryland, United States|2021-05-31 20:15:13 UTC|
|kapa2_app          |http://d.liveatc.net/kapa2_app          |KAPA App/Dep                      |US-Class-B|KAPA 311953Z 36003KT 10SM SCT018 BKN047 BKN075 14/07 A3029 RMK AO2 SLP232 T01390072 |Denver, Colorado, United States      |2021-05-31 20:15:13 UTC|

## TODO
- Dispatch Large Scale Listener to (10 airports maybe)?
  - Need to isolate the output from each other, or we do docker run, not sure what's the plan yet
- Use database to manage the audio information
- Perhaps attach to a Cloud (AWS)?