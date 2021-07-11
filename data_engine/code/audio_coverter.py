#!/usr/local/bin/python

import pydub
import os
import datetime
import asyncio

def file_timestamp_beyond_current(filename, current_time=None):
    current_time = current_time or datetime.datetime.now()
    end_time_stamp = filename.rstrip(".mp3").split("-")[-1]
    end_time = datetime.datetime.strptime(end_time_stamp, "%Y%m%d%H%M%S%f") # takes no keyword argument
    if end_time > current_time:
        return False
    else:
        return True

async def audio_convert(raw_audio_dir, processed_audio_dir, min_silence_len=500, silence_thresh=-40, extend=10):

    current_time = datetime.datetime.now()
    raw_audio_names = [fname for fname in os.listdir(raw_audio_dir) if file_timestamp_beyond_current(fname, current_time)]
    raw_audio_paths = [os.path.join(raw_audio_dir, fname) for fname in raw_audio_names]
    print(f"[converter] found {len(raw_audio_names)} files qualified to be converted")
    for raw_audio_name, raw_audio_path in zip(raw_audio_names, raw_audio_paths):
        raw_audio_file = await pydub.AudioSegment.from_mp3(raw_audio_path)
        offset_lists = await pydub.silence.detect_nonsilent(
            raw_audio_file,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh
        )
        for (start_offset, end_offset) in offset_lists:
            rec_start_offset = max(start_offset-extend, 0)
            rec_end_offset = min(end_offset+extend, len(raw_audio_file))
            chunk = raw_audio_file[rec_start_offset:rec_end_offset]
            offset_str = f"{rec_start_offset}-{rec_end_offset}"
            export_filename = os.path.join(
                processed_audio_dir,
                raw_audio_name.replace(".mp3", f"-{offset_str}.mp3")
            )
            print(f"[converter] converted and exported sound slice {export_filename}")
            await chunk.export(export_filename, format="mp3")
        os.remove(raw_audio_path)
    return