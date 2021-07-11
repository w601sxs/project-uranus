#!/usr/local/bin/python

import ffmpeg
import os
import datetime
import logging

class AudioStream(object):
    def __init__(self, url, flag=None):

        self.url = url
        self.flag = flag or url.split('/')[-1]
        self.probe = None
        self.stream = None
        self.codec_type = None
        self.channels = None
        self.samplerate = None

    def describe(self):
        display_info = {
            "target_url": self.url,
            "flag": self.flag,
            "codec_type": self.codec_type,
            "channels": self.channels,
            "samplerate": self.samplerate
        }
        logging.info(f"[{self.flag}] Acquired Stream Info: {display_info}")
        return

    def get_probe(self):
        try:
            probe = ffmpeg.probe(
                self.url, loglevel='error'
            )
        except ffmpeg.Error as e:
            logging.info(f"[{self.flag}] Stream <{self.url}> is not available due to Exception: {e.stderr}")
        except BaseException as e:
            logging.info(f"[{self.flag}] Stream <{self.url}> is not available due to Exception: {e}")
        else:
            self.probe = probe
            streams = self.probe.get("streams", [])
            assert len(streams) == 1, \
                f'[{self.flag}] Ternimated due to: there must be exactly one stream available'
            self.stream = streams[0]
            self.codec_type = self.stream.get("codec_type", None)
            assert self.codec_type == 'audio', \
                f'[{self.flag}] Ternimated due to: The stream must be an audio stream'
            self.channels = self.stream.get("channels", None)
            self.samplerate = self.stream.get('sample_rate', None)
            self.describe()
        finally:
            return self

    def get_record_cmd(self, runtime, export_dir):
        current_time = datetime.datetime.now()
        start_time_stamp = current_time.strftime("%Y%m%d%H%M%S%f")[:-3]
        duration = datetime.timedelta(seconds=runtime)
        duration_time_stamp = str(duration)
        end_time = current_time + duration
        end_time_stamp = end_time.strftime("%Y%m%d%H%M%S%f")[:-3]
        export_path = os.path.join(export_dir, f"{self.flag}-{start_time_stamp}-{end_time_stamp}.mp3")
        cmd = " ".join([
            "ffmpeg",
            "-i", str(self.url),
            "-t", str(duration_time_stamp),
            "-ac", str(self.channels),
            "-ar", str(self.samplerate),
            "-loglevel", "error",
            export_path
        ])
        return cmd

if __name__ == "__main__":
    test_stream = AudioStream('http://d.liveatc.net/kbos_twr')
    os.makedirs("./liveatc-flight-sonar/tmp/", exist_ok=True)
    test_stream.save_manifest_file("./liveatc-flight-sonar/tmp/")
    test_stream.get_probe()
    test_stream.get_record_cmd(runtime=120, export_dir="./liveatc-flight-sonar/tmp/raw_audio/")