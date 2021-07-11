#!/usr/local/bin/python

from cProfile import run
from genericpath import exists
import os
import asyncio
import psutil
import subprocess
from stream_recorder import AudioStream
from stream_finder import crawl_stream_info
import time
import json
import datetime
import pydub

def file_timestamp_beyond_current(filename, current_time=None):
    current_time = current_time or datetime.datetime.now()
    end_time_stamp = filename.rstrip(".mp3").split("-")[-1]
    end_time = datetime.datetime.strptime(end_time_stamp, "%Y%m%d%H%M%S%f") # takes no keyword argument
    if end_time > current_time:
        return False
    else:
        return True

async def deploy_listener(audio_stream, session_runtime=600, run_interval=60, raw_audio_dir=None):
    pid = None
    try:
        while True:
            if pid is not None:
                monitor_process = psutil.Process(pid)
                start_time = monitor_process.create_time()
                process_runtime = time.time() - start_time
                process_status = monitor_process.status()
                if monitor_process.status() not in ['zombie', 'dead']:
                    print(f"[{audio_stream.flag}] ffmpeg Process Running in [{pid} >> {process_status}], ({process_runtime:.2f}s)")
                    await asyncio.sleep(run_interval)
                    continue
                else:
                    pid = None
            if audio_stream.probe is None:
                audio_stream.get_probe()
            # by this time audio_stream should acquire probe, if not wait for x sec
            if audio_stream.probe is None:
                print(f"[{audio_stream.flag}] Retry Fetching Probe in {run_interval}s")
                await asyncio.sleep(run_interval)
            else:
                cmd = audio_stream.get_record_cmd(runtime=session_runtime, export_dir=raw_audio_dir)
                sub_process = subprocess.Popen(cmd, shell=True)
                pid = sub_process.pid
    except BaseException as e:
        print(f"[{audio_stream.flag}] Terminate this process due to exception {e}")
        return

async def deploy_converter(raw_audio_dir, processed_audio_dir, run_interval=60, min_silence_len=500, silence_thresh=-40, extend=10):
    try:
        while True:
            print(f"[stream converter] Converter start")
            current_time = datetime.datetime.now()
            raw_audio_names = [fname for fname in os.listdir(raw_audio_dir) if file_timestamp_beyond_current(fname, current_time)]
            raw_audio_paths = [os.path.join(raw_audio_dir, fname) for fname in raw_audio_names]
            print(f"[stream converter] found {len(raw_audio_names)} files qualified to be converted")
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
                    print(f"[stream converter] converted and exported sound slice {export_filename}")
                    await chunk.export(export_filename, format="mp3")
                os.remove(raw_audio_path)
            print(f"[stream converter] Process finished, next rerun in {run_interval}s")
            await asyncio.sleep(run_interval)
    except BaseException as e:
        print(f"[stream converter] Terminate this process due to exception {e}")
        return

async def main(data_dir, tryrun=None, flag_cond=None, run_interval=20, converter_rerun_interval=60):

    raw_audio_dir = os.path.join(data_dir, "raw_audios")
    processed_audio_dir = os.path.join(data_dir, "processed_audios")
    stream_info_dir = os.path.join(data_dir, "stream_info")
    stream_info_path = os.path.join(stream_info_dir, "stream_info.json")

    for directory in [raw_audio_dir, processed_audio_dir, stream_info_dir]:
        os.makedirs(directory, exist_ok=True)

    crawl_stream_info(stream_info_path)
    try:
        with open(stream_info_path, mode="r") as f:
            streams = [AudioStream(item["stream_link"]) for item in json.load(f)]
            if flag_cond is not None:
                streams = [item for item in streams if flag_cond in item.flag]
                print(f"[main] Filtered flag includes {flag_cond}, total {len(streams)} streams")
            if tryrun is not None:
                streams = streams[:tryrun]
                print(f"[main] Try run: {len(streams)} streams")
            tasks = [deploy_converter(raw_audio_dir, processed_audio_dir, run_interval=converter_rerun_interval)]
            tasks += [deploy_listener(stream, raw_audio_dir=raw_audio_dir, run_interval=run_interval) for stream in streams]
            tasks.append(deploy_converter(raw_audio_dir, processed_audio_dir))
        await asyncio.gather(*tasks)
    except BaseException:
        print(f"[main] Terminated ...")
        os._exit(0)

if __name__ == "__main__":
    asyncio.run(main(data_dir="/home/ruyyi/devs/project-uranus/data", flag_cond="kbos"))

