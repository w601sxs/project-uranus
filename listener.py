import os
import datetime
import subprocess
import json

class AudioStream(object):
    def __init__(self, url, flag, probe):

        self.url = url
        self.flag = flag
        self.probe = probe
        self.stream = None
        self.codec_type = None
        self.channels = None
        self.samplerate = None

        streams = self.probe.get("streams", [])
        assert len(streams) == 1, \
            'Ternimated due to: there must be exactly one stream available'
        
        self.stream = streams[0]
        self.codec_type = self.stream.get("codec_type", None)
        assert self.codec_type == 'audio', \
            'Ternimated due to: The stream must be an audio stream'
        self.channels = self.stream.get("channels", None)
        self.samplerate = self.stream.get('sample_rate', None)
        self.describe()

    def describe(self):
        display_info = {
            "target_url": self.url,
            "flag": self.flag,
            "codec_type": self.codec_type,
            "channels": self.channels,
            "samplerate": self.samplerate
        }
        print(f"Acquired Stream Info: {display_info}")
        return 
        
    def save_manifest_file(self, manifest_dir):
        manifest_fpath = os.path.join(manifest_dir, f"{self.flag}.json")
        print(f"Save Manifest File to {manifest_fpath}")
        os.makedirs(os.path.dirname(manifest_fpath), exist_ok=True)
        with open(manifest_fpath, mode="w") as f:
            json.dump(self.__dict__, f, indent=2)

def deploy_listener_main(url, probe, flag, data_dir, runtime):

    manifest_dir = os.path.join(data_dir, "manifests")
    raw_audio_dir = os.path.join(data_dir, "raw_audio")

    print(f'Deploy ffmpeg probe on URL: {url}')
    audio_stream = AudioStream(url, flag, probe)
    audio_stream.save_manifest_file(manifest_dir)
    current_time = datetime.datetime.now()
    duration = datetime.timedelta(seconds=runtime)
    end_time = current_time + duration
    start_time_stamp = current_time.strftime("%Y%m%d%H%M%S%f")[:-3]
    end_time_stamp = end_time.strftime("%Y%m%d%H%M%S%f")[:-3]
    duration_time_stamp = str(duration)
    raw_audio_path = os.path.join(
        raw_audio_dir, 
        f"{audio_stream.flag}-{start_time_stamp}-{end_time_stamp}.mp3"
    )
    cmd = " ".join(
        [
            "ffmpeg", 
            "-i", str(audio_stream.url),
            "-t", str(duration_time_stamp),
            "-ac", str(audio_stream.channels),
            "-ar", str(audio_stream.samplerate),
            "-loglevel", "error",
            raw_audio_path
        ]
    )
    try:
        print(f"... Execute {cmd}")
        subprocess.check_output(cmd, shell=True)
    except Exception as e:
        print(f"[{audio_stream.flag}] Terminated due to exception {e}")
    finally:
        return