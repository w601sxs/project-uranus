from metaflow import FlowSpec, step, Parameter
from stream_finder import crawl_stream_info
from initiate import setup
from listener import deploy_listener_main
from converter import deploy_converter_main
import os
import json
import ffmpeg

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
    listener_runtime = Parameter(
        "listener_runtime",
        help="runtime of a listener",
        default=3600
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
    back_door = Parameter(
        "back_door",
        help="back_door_flag, if True if we'll skip some of the process or limit the deployed resources",
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
        if not self.back_door is True or not os.path.exists(self.stream_info_path):
            self.stream_info_records = crawl_stream_info(self.stream_info_path)
        else:
            print("Found existing stream info in data directory, skipped")
            with open(self.stream_info_path, mode="r") as f:
                self.stream_info_records = json.load(f)
        self.next(self.deploy_listerners)

    @step
    def deploy_listerners(self):
        if self.back_door is True:
            self.use_agents = self.stream_info_records[:5]
        else:
            self.use_agents = self.stream_info_records
        if self.dry_run is True:
            cmd = "rm -f " + os.path.join(self.data_dir, "manifests/*")
            os.system(cmd)
            cmd = "rm -f " + os.path.join(self.data_dir, "raw_audio/*")
            os.system(cmd)
        self.next(self.deploy_listener, foreach="use_agents")

    @step
    def deploy_converter(self):
        if self.dry_run is True:
            cmd = "rm -f " + os.path.join(self.data_dir, "processed_audio/*")
            os.system(cmd)
        deploy_converter_main(
            self.data_dir
        )
        self.next(self.end)
        

    @step
    def deploy_listener(self):
        self.listener_info = self.input
        self.url = self.listener_info["stream_link"]
        self.flag = self.url.split("/")[-1]
        print(f"[{self.flag}] Listener targeting on URL: {self.url}")
        if self.back_door == True:
            listener_runtime = 3600
        else:
            listener_runtime = self.listener_runtime
        try:
            self.probe = ffmpeg.probe(
                self.url, 
                loglevel="error"
            )
        except ffmpeg.Error as e:
            print(f"[{self.flag}] Terminate due to exception: {e.stderr.decode().strip()}")
        except Exception as e:
            print(f"[{self.flag}] Terminate due to exception: {e}")
        else:
            print(f"[{self.flag}] Captured probe, proceed")
            deploy_listener_main(
                url = self.url,
                flag = self.flag,
                probe = self.probe, 
                data_dir = self.data_dir,
                runtime = listener_runtime,
            )
        self.next(self.join_listeners)

    @step
    def join_listeners(self, inputs):
        self.next(self.deploy_converter)

    # @step
    # def join_mainflow(self, inputs):
    #     self.next(self.end)

    @step
    def end(self):
        pass

if __name__ == "__main__":
    AudioCrawlingFLow()
