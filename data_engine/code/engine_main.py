#!/usr/local/bin/python

from cProfile import run
import os
import asyncio
import psutil
import subprocess
from stream_recorder import AudioStream
from stream_finder import crawl_stream_info
import time
import json
import logging

logging.basicConfig(
     level=logging.INFO, 
     format= '%(asctime)s > %(funcName)s:%(levelname)s >> %(message)s',
     datefmt='%Y-%m-%d %H:%M:%S %Z'
 )

_asyncio_short_waittime = 0.01

async def deploy_listener(audio_stream, session_runtime=300, run_interval=60, raw_audio_dir=None):
    pid = None
    try:
        while True:
            if pid is not None:
                monitor_process = psutil.Process(pid)
                start_time = monitor_process.create_time()
                process_runtime = time.time() - start_time
                process_status = monitor_process.status()
                if monitor_process.status() not in ['zombie', 'dead']:
                    logging.info(f"[{audio_stream.flag}] ffmpeg Process Running in [{pid} >> {process_status}], ({process_runtime:.2f}s)")
                    await asyncio.sleep(run_interval)
                    continue
                else:
                    pid = None
            if audio_stream.probe is None:
                audio_stream.get_probe()
            # by this time audio_stream should acquire probe, if not wait for x sec
            if audio_stream.probe is None:
                logging.info(f"[{audio_stream.flag}] Retry Fetching Probe in {run_interval}s")
                await asyncio.sleep(run_interval)
            else:
                cmd = audio_stream.get_record_cmd(runtime=session_runtime, export_dir=raw_audio_dir)
                sub_process = subprocess.Popen(cmd, shell=True)
                pid = sub_process.pid
                await asyncio.sleep(_asyncio_short_waittime)
    except BaseException as e:
        logging.warning(f"[{audio_stream.flag}] Terminate this process due to exception {e}")
        return

async def main_procedure(data_dir, tryrun=None, flag_cond=None, run_interval=60, 
listener_session_runtime=600):

    raw_audio_dir = os.path.join(data_dir, "raw_audios")
    stream_info_dir = os.path.join(data_dir, "stream_info")
    stream_info_path = os.path.join(stream_info_dir, "stream_info.json")

    for directory in [raw_audio_dir, stream_info_dir]:
        os.makedirs(directory, exist_ok=True)

    # initiate stream info
    crawl_stream_info(stream_info_path)

    # main loop start
    try:
        with open(stream_info_path, mode="r") as f:
            stream_info_raw = json.load(f)
            logging.info("[main] Successfully loaded stream info file")
            streams = [AudioStream(item["stream_link"]) for item in stream_info_raw]
            if flag_cond is not None:
                flag_cond = flag_cond.split(",")
                logging.info(f"[main] Detected {len(flag_cond)} flag conditions")
                streams = [
                    item for item in streams 
                    if any(flag_cond_meta in item.flag for flag_cond_meta in flag_cond)
                ]
                logging.info(f"[main] Filtered flag includes [{flag_cond}], total {len(streams)} streams")
            if tryrun is not None:
                streams = streams[:tryrun]
                logging.info(f"[main] Try run: {len(streams)} streams")
            tasks = [
                deploy_listener(
                    stream, raw_audio_dir=raw_audio_dir, 
                    session_runtime=listener_session_runtime, 
                    run_interval=run_interval
                ) 
                for stream in streams
            ]
        await asyncio.gather(*tasks)
    except Exception as e:
        logging.warning(f"[main] Terminated due to exception {e}...")
    except BaseException:
        logging.warning(f"[main] Terminated ...")
        os._exit(0)

if __name__ == "__main__":

    run_config = {
        "data_dir": os.environ.get("DATA_DIR", "./data"),
        "flag_cond": os.environ.get("FLAG_COND", None),
        "run_interval": os.environ.get("RUN_INTERVAL", 60),
        "tryrun": os.environ.get("TRYRUN", None),
        "listener_session_runtime": os.environ.get("LISTENER_SESSION_RUNTIME", 600),
    }

    for k, v in run_config.items():
        if k in ["tryrun", "run_interval", "converter_rerun_interval", "listener_session_runtime"]:
            run_config[k] = int(v) if v is not None else None
        logging.info(f"[main] run config: {k}: {v} ({type(v)})")

    asyncio.run(
        main_procedure(**run_config)
    )

