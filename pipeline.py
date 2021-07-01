from metaflow import FlowSpec, step, Parameter
from stream_finder import crawl_stream_info
from initiate import setup
import os
import json

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
    dry_run = Parameter(
        "dry_run",
        help="dry run flag, if True, remove the existing data directory when run the pipeline",
        default=False
    )
    safe_mode = Parameter(
        "safe_mode",
        help="safe_mode_falg, if True if limits the number of listeners to be 3",
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
        if self.dry_run is True or not os.path.exists(self.stream_info_path):
            self.stream_info_records = crawl_stream_info(self.stream_info_path)
        else:
            print("Found existing stream info in data directory, skipped")
            with open(self.stream_info_path, mode="r") as f:
                self.stream_info_records = json.load(f)
        if self.safe_mode is True:
            self.stream_info_records = self.stream_info_records[:3]
        self.next(self.dispatch_listener, foreach="stream_info_records")

    @step
    def dispatch_listener(self):
        self.listener_info = self.input
        print("Listener targeting on URL: {}".format(self.listener_info["stream_link"]))
        
        self.next(self.join)

    @step
    def join(self, inputs):
        self.next(self.end)

    @step
    def end(self):
        pass

if __name__ == "__main__":
    AudioCrawlingFLow()
