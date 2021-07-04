from metaflow import FlowSpec, step, Parameter
from stream_finder import crawl_stream_info
from initiate import setup
from listener import deploy_listener_main
from converter import deploy_converter_main
import os
import json
import ffmpeg
import datetime
import time

class AudioCrawlingFLow(FlowSpec):

    data_dir = Parameter(
        "data_dir",
        help="the directory to store all the intermediate and final data",
        default="data"
    )
    stream_info_path = Parameter(
        "stream_info_path",
        help="the json file path to export the stream info generated from step find_streams",
        default="data/stream_info/stream_info.json"
    )
    max_listener_runtime = Parameter(
        "max_listener_runtime",
        help="runtime of a listener, including the retrials",
        default=86400
    )
    session_listener_runtime = Parameter(
        "session_listener_runtime",
        help="once connected to the live stream, ffmpeg will output the file every this number of seconds",
        default=3600
    )
    retry_interval = Parameter(
        "retry_interval",
        help="when failed connected to the stream, pipeline will retry the connection in this number of seconds",
        default=300
    )
    min_silence_len = Parameter(
        "min_silence_len",
        help="silence interval in one audio segment (ms)",
        default=500
    )
    silence_thresh = Parameter(
        "silence_thresh",
        help="threshold of volume in audio segment we treat as silence status (DB)",
        default=-40
    )
    extend = Parameter(
        "extend",
        help="time that we extend each audio segment (ms)",
        default=10
    )
    dry_run = Parameter(
        "dry_run",
        help="dry run flag, if True, remove the existing data directory when run the pipeline",
        default=False
    )
    debug_limit_runtime = Parameter(
        "debug_limit_runtime",
        help="debug_limit_runtime flag, if True if we'll limit the runtime of the listener",
        default=False
    )
    debug_skip_fetch_stream = Parameter(
        "debug_skip_fetch_stream",
        help="debug_skip_fetch_stream flag, if True if we'll skip pulling stream if exist",
        default=False
    )
    debug_limit_stream = Parameter(
        "debug_limit_stream",
        help="debug_limit_stream flag, if True if we'll limit the number of stream we use to deploy listener",
        default=False
    )

    @step
    def start(self):
        print(f"Setup with data directory: {os.path.abspath(self.data_dir)}")
        setup(self.data_dir, self.dry_run)
        self.next(self.find_streams)

    @step
    def find_streams(self):
        print("Entering stream searching")
        print(f"expected export the stream info path to {os.path.abspath(self.stream_info_path)}")
        if not self.debug_skip_fetch_stream is True or not os.path.exists(self.stream_info_path):
            self.stream_info_records = crawl_stream_info(self.stream_info_path)
        else:
            print("Found existing stream info in data directory, skipped")
            with open(self.stream_info_path, mode="r") as f:
                self.stream_info_records = json.load(f)
        self.next(self.deployment)

    @step
    def deployment(self):
        if self.debug_limit_stream is True:
            self.use_streams = self.stream_info_records[:5]
        else:
            self.use_streams = self.stream_info_records
        if self.dry_run is True:
            cmd = "rm -f " + os.path.join(self.data_dir, "manifests/*")
            os.system(cmd)
            cmd = "rm -f " + os.path.join(self.data_dir, "raw_audio/*")
            os.system(cmd)
            cmd = "rm -f " + os.path.join(self.data_dir, "processed_audio/*")
            os.system(cmd)
        self.next(self.deployment_meta, foreach="use_streams") 

    @step
    def deployment_meta(self):
        self.listener_info = self.input
        self.url = self.listener_info["stream_link"]
        self.flag = self.url.split("/")[-1]
        print(f"[{self.flag}] Listener targeting on URL: {self.url}")
        start_time = datetime.datetime.now()
        if self.debug_limit_runtime == True:
            session_listener_runtime = 120
            max_listener_runtime = 120
        else:
            session_listener_runtime = min(self.max_listener_runtime, 3600)
            max_listener_runtime = self.max_listener_runtime
        print(f"[{self.flag}] Maximum Runtime: {max_listener_runtime}s, Session Runtime: {session_listener_runtime}s")
        ## convert if raw_audio has remaining files
        deploy_converter_main(
            self.data_dir,
            self.flag
        )
        while True:
            if (datetime.datetime.now() - start_time).seconds > max_listener_runtime:
                print(f"[{self.flag}] Reached the maximum runtime, terminate this step")
                break
            else:
                try:
                    self.probe = ffmpeg.probe(
                        self.url, 
                        loglevel="error"
                    )
                except ffmpeg.Error as e:
                    print(f"[{self.flag}] Failed due to exception: {e.stderr.decode().strip()}")
                    print(f"[{self.flag}] Retry connection in: {self.retry_interval} seconds")
                    time.sleep(self.retry_interval)
                except Exception as e:
                    print(f"[{self.flag}] Failed due to exception: {e}")
                    print(f"[{self.flag}] Retry connection in: {self.retry_interval} seconds")
                    time.sleep(self.retry_interval)
                else:
                    print(f"[{self.flag}] Captured probe, proceed")
                    ## proceed to fetch the raw_audios
                    deploy_listener_main(
                        url = self.url,
                        flag = self.flag,
                        probe = self.probe, 
                        data_dir = self.data_dir,
                        runtime = session_listener_runtime
                    )
                    ## proceeed to split the audios
                    print(f"[{self.flag}] Start converting raw audio")
                    deploy_converter_main(
                        self.data_dir,
                        self.flag
                    )
        self.next(self.join_deployment)

    @step
    def join_deployment(self, inputs):
        self.next(self.end)

    @step
    def end(self):
        pass

if __name__ == "__main__":
    AudioCrawlingFLow()
