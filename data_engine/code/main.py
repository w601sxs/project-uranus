#!/usr/local/bin/python

from cProfile import run
import os
import asyncio
import psutil
import subprocess
from stream_recorder import AudioStream
from stream_finder import crawl_stream_info
from ast import literal_eval
import time
import json
import datetime
import pydub
import boto3
from urllib.parse import urlparse
from botocore.exceptions import ClientError
import logging

logging.basicConfig(
     level=logging.INFO, 
     format= '%(asctime)s > %(funcName)s:%(levelname)s >> %(message)s',
     datefmt='%Y-%m-%d %H:%M:%S %Z'
 )

def file_timestamp_beyond_current(filename, current_time=None):
    current_time = current_time or datetime.datetime.now()
    end_time_stamp = filename.rstrip(".mp3").split("-")[-1]
    end_time = datetime.datetime.strptime(end_time_stamp, "%Y%m%d%H%M%S%f") # takes no keyword argument
    if end_time > current_time:
        return False
    else:
        return True

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
                await asyncio.sleep(0.01)
    except BaseException as e:
        logging.warning(f"[{audio_stream.flag}] Terminate this process due to exception {e}")
        return

async def deploy_converter(raw_audio_dir, processed_audio_dir, run_interval=60, min_silence_len=500, silence_thresh=-40, extend=10):
    try:
        while True:
            logging.info(f"[stream converter] Converter start")
            current_time = datetime.datetime.now()
            raw_audio_names = [fname for fname in os.listdir(raw_audio_dir) if file_timestamp_beyond_current(fname, current_time)]
            raw_audio_paths = [os.path.join(raw_audio_dir, fname) for fname in raw_audio_names]
            logging.info(f"[stream converter] found {len(raw_audio_names)} files qualified to be converted")
            for raw_audio_name, raw_audio_path in zip(raw_audio_names, raw_audio_paths):
                try:
                    if os.path.exists(raw_audio_path):
                        raw_audio_file = pydub.AudioSegment.from_mp3(raw_audio_path)
                        await asyncio.sleep(2)
                        offset_lists = pydub.silence.detect_nonsilent(
                            raw_audio_file,
                            min_silence_len=min_silence_len,
                            silence_thresh=silence_thresh
                        )
                        await asyncio.sleep(2)
                        for (start_offset, end_offset) in offset_lists:
                            rec_start_offset = max(start_offset-extend, 0)
                            rec_end_offset = min(end_offset+extend, len(raw_audio_file))
                            chunk = raw_audio_file[rec_start_offset:rec_end_offset]
                            offset_str = f"{rec_start_offset}-{rec_end_offset}"
                            export_filename = os.path.join(
                                processed_audio_dir,
                                raw_audio_name.replace(".mp3", f"-{offset_str}.mp3")
                            )
                            logging.info(f"[stream converter] converted and exported sound slice {export_filename}")
                            chunk.export(export_filename, format="mp3")
                except Exception as e:
                     logging.error(f"[stream converter] Failed to convert due to exception {e}")
                finally:
                    raw_audio_file = None
                    offset_lists = None
                    chunk = None
                    os.remove(raw_audio_path)
                    await asyncio.sleep(0.01)
            logging.info(f"[stream converter] Process finished, next rerun in {run_interval}s")
            await asyncio.sleep(run_interval)
    except BaseException as e:
        logging.warning(f"[stream converter] Terminate this process due to exception {e}")
        return

async def s3_upload(processed_audio_dir, s3_processed_audio_dir, profile=None, run_interval=60):
    try:
        while True:
            if profile is not None:
                session = boto3.Session()
            else:
                session = boto3.Session(profile_name=profile)
            s3_client = session.client("s3")
            for fname in os.listdir(processed_audio_dir):
                source_path = os.path.join(processed_audio_dir, fname)
                s3_path = os.path.join(s3_processed_audio_dir, fname)
                parsed_s3_path = urlparse(s3_path)
                bucket = parsed_s3_path.netloc
                key = parsed_s3_path.path.lstrip("/")
                await asyncio.sleep(0.01)
                s3_client.upload_file(source_path, bucket, key)
                logging.info(f"[s3 uploader] uploaded file {fname}")
                os.remove(source_path)
            logging.info(f"[stream converter] Process finished, next rerun in {run_interval}s")
            await asyncio.sleep(run_interval)
    except ClientError as e:
        logging.error(f"[s3 uploader] terminated process due to client error {e}")
    except BaseException as e:
        logging.warning(f"[s3 uploader] terminated process due to exception {e}")
    finally:
        s3_client = None
        session = None
        return

async def main_procedure(data_dir, tryrun=None, flag_cond=None, run_interval=60, 
converter_rerun_interval=100, listener_session_runtime=600, s3_processed_audio_dir=None, aws_profile=None):

    raw_audio_dir = os.path.join(data_dir, "raw_audios")
    processed_audio_dir = os.path.join(data_dir, "processed_audios")
    stream_info_dir = os.path.join(data_dir, "stream_info")
    stream_info_path = os.path.join(stream_info_dir, "stream_info.json")

    for directory in [raw_audio_dir, processed_audio_dir, stream_info_dir]:
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
                streams = [item for item in streams if flag_cond in item.flag]
                logging.warning(f"[main] Filtered flag includes {flag_cond}, total {len(streams)} streams")
            if tryrun is not None:
                streams = streams[:tryrun]
                logging.warning(f"[main] Try run: {len(streams)} streams")
            tasks = [
                deploy_converter(
                    raw_audio_dir, processed_audio_dir, 
                    run_interval=converter_rerun_interval
                )
            ]
            if s3_processed_audio_dir is not None:
                tasks += [
                    s3_upload(
                        processed_audio_dir, 
                        s3_processed_audio_dir, 
                        profile=aws_profile,
                        run_interval=run_interval,
                    )
                ]
            tasks += [
                deploy_listener(
                    stream, raw_audio_dir=raw_audio_dir, 
                    session_runtime=listener_session_runtime, 
                    run_interval=run_interval
                ) 
                for stream in streams
            ]
        await asyncio.gather(*tasks)
    except Exception as e:
        logging.info(f"[main] Terminated due to exception {e}...")
    except BaseException:
        logging.info(f"[main] Terminated ...")
        os._exit(0)

if __name__ == "__main__":

    run_config = {
        "data_dir": os.environ.get("DATA_DIR", "./data"),
        "flag_cond": os.environ.get("FLAG_COND", None),
        "run_interval": os.environ.get("RUN_INTERVAL", 60),
        "tryrun": os.environ.get("TRYRUN", None),
        "converter_rerun_interval": os.environ.get("CONVERTER_RUN_INTERVAL", 100),
        "listener_session_runtime": os.environ.get("LISTENER_SESSION_RUNTIME", 600),
        "s3_processed_audio_dir": os.environ.get("S3_PROCESSED_AUDIO_DIR", None),
        "aws_profile": os.environ.get("AWS_PROFILE", None)
    }

    for k, v in run_config.items():
        if k in ["tryrun", "run_interval", "converter_rerun_interval", "listener_session_runtime"]:
            run_config[k] = int(v) if v is not None else None
        logging.info(f"[main] run config: {k}: {v} ({type(v)})")

    asyncio.run(
        main_procedure(**run_config)
    )

