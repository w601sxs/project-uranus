#!/usr/local/bin/python

import os
import datetime
import pydub
import logging
import time

logging.basicConfig(
     level=logging.INFO, 
     format= '%(asctime)s > %(funcName)s:%(levelname)s >> %(message)s',
     datefmt='%Y-%m-%d %H:%M:%S %Z'
 )

_timestamp_fmt = "%Y%m%d%H%M%S%f"

def parse_file_name(filename):
    pieces = filename.rstrip(".mp3").split("-")
    start_time_stamp = pieces[-2]
    end_time_stamp = pieces[-1]
    start_time = datetime.datetime.strptime(start_time_stamp, _timestamp_fmt)
    end_time = datetime.datetime.strptime(end_time_stamp, _timestamp_fmt)
    return {
        "file_name": filename,
        "start_time_stamp": start_time_stamp,
        "end_time_stamp": end_time_stamp,
        "start_time": start_time, 
        "end_time": end_time
    }

def file_timestamp_beyond_current(end_time, current_time=None):
    current_time = current_time or datetime.datetime.now()
    if end_time > current_time:
        return False
    else:
        return True

def make_convert(data_dir, run_interval=60, min_silence_len=500, silence_thresh=-40, extend=10):

    raw_audio_dir = os.path.join(data_dir, "raw_audios")
    processed_audio_dir = os.path.join(data_dir, "processed_audios")

    for directory in [raw_audio_dir, processed_audio_dir]:
        os.makedirs(directory, exist_ok=True)

    logging.info(f"[stream converter] Converter start")
    current_time = datetime.datetime.now()
    raw_audio_infos = [
        parse_file_name(fname) 
        for fname in os.listdir(raw_audio_dir)
    ]
    available_audio_infos = [
        info_dict
        for info_dict in raw_audio_infos
        if file_timestamp_beyond_current(info_dict["end_time"], current_time)
    ]
    available_fpaths = [
        os.path.join(raw_audio_dir, info_dict["file_name"]) 
        for info_dict in available_audio_infos
    ]
    logging.info(f"[stream converter] found {len(available_audio_infos)} files qualified to be converted")
    for info_dict, audio_path in zip(available_audio_infos, available_fpaths):
        logging.info(f"[stream converter] Handling File {audio_path}")
        try:
            if os.path.exists(audio_path):
                raw_audio_file = pydub.AudioSegment.from_mp3(audio_path)
                sub_export_dir = datetime.datetime.strftime(info_dict["end_time"], "%Y-%m-%d-%H")
                offset_lists = pydub.silence.detect_nonsilent(
                    raw_audio_file,
                    min_silence_len=min_silence_len,
                    silence_thresh=silence_thresh
                )
                logging.info(f"[stream converter] File {info_dict['file_name']} parsed {len(offset_lists)} segments")
                for (start_offset, end_offset) in offset_lists:
                    rec_start_offset = max(start_offset-extend, 0)
                    rec_end_offset = min(end_offset+extend, len(raw_audio_file))
                    chunk = raw_audio_file[rec_start_offset:rec_end_offset]
                    offset_str = f"{rec_start_offset}-{rec_end_offset}"
                    export_filepath = os.path.join(
                        processed_audio_dir, 
                        sub_export_dir,
                        info_dict["file_name"].replace(".mp3", f"-{offset_str}.mp3")
                    )
                    export_dirname = os.path.dirname(export_filepath)
                    os.makedirs(export_dirname, exist_ok=True)
                    logging.info(f"[stream converter] converted and exported sound slice {export_filepath}")
                    chunk.export(export_filepath, format="mp3")
        except Exception as e:
                logging.error(f"[stream converter] Failed to convert due to exception {e}, remove source file anyway")
        finally:
            raw_audio_file = None
            offset_lists = None
            chunk = None
            os.remove(audio_path)
    logging.info(f"[stream converter] Process finished, next rerun in {run_interval}s")
    time.sleep(run_interval)
    return

if __name__ == "__main__":
    run_config = {
        "data_dir": os.environ.get("DATA_DIR", "./data"),
        "run_interval": os.environ.get("RERUN", 60),
    }

    for k, v in run_config.items():
        if k in ["run_interval"]:
            run_config[k] = int(v) if v is not None else None
        logging.info(f"[main] run config: {k}: {v} ({type(v)})")

    make_convert(**run_config)
