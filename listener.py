import ffmpeg
import sys
import os
import subprocess
import json
import numpy as np
import logging
import datetime

logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] > %(filename)s:%(funcName)s >> %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S'
)
class NumpyAudioFrame(object):
    def __init__(self, frame_vector, prec=3):
        self.frame_vector = frame_vector
        self.dim = frame_vector.shape
        if self.dim[0] != 0:
            self.min = frame_vector.min()
            self.max = frame_vector.max()
            self.avg = frame_vector.mean()
            self.retain = int(np.round(self.avg, prec) != 0)
        else:
            self.min = 0
            self.max = 0
            self.avg = 0
            self.retain = -1

    def __repr__(self):
        if self.retain == 1:
            return "Frame --> Shape: {}, Avg: {:.3f}, Max: {:.3f}, Min: {:.3f}".format(self.dim, self.avg, self.max, self.min)
        elif self.retain == 0:
            return "Frame --> Shape: {}".format(self.dim)

class AudioStream(object):
    def __init__(self, url, raw_stream_file_path=None):

        self.url = url
        self.flag = url.split("/")[-1]
        self.raw_stream_file_path = raw_stream_file_path or f"./data/raw_stream/{self.flag}.stream"

        try:
            probe = ffmpeg.probe(url)
        except ffmpeg.Error as e:
            logging.info(f"Terminate due to ffmpeg error: {e}")
            sys.exit(1)
        except Exception as e:
            logging.info(f"Terminate due to: {e}")
            sys.exit(1)
        else:
            logging.info(f"Captured Probe ...")
            self.url = url
            self.flag = url.split("/")[-1]
            self.probe = probe
            streams = self.probe.get("streams", [])
            assert len(streams) == 1, \
                'Ternimated due to: There must be exactly one stream available'
            
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
            "samplerate": self.samplerate,
            "raw_stream_file_path": self.raw_stream_file_path
        }
        print(f"Acquired Stream Info: \n {json.dumps(display_info, indent=2)}")
        
    def save_manifest_file(self, manifest_dir):
        manifest_fpath = os.path.join(manifest_dir, f"{self.flag}.json")
        logging.warning(f"Save Manifest File to {manifest_fpath}")
        os.makedirs(os.path.dirname(manifest_fpath), exist_ok=True)
        with open(manifest_fpath, mode="w") as f:
            json.dump(self.__dict__, f, indent=2)

def listen_main(url:str, blocksize:int=1024, retain:int=5, data_dir:str=None):
    """listen to atc stream, save the useful audio snippet to raw_audio_dir
    and generate the manifest file save to manifest_dir

    Args:
        url (str): [description]
        device (str, optional): [description]. Defaults to None.
        blocksize (int, optional): [description]. Defaults to 1024.
        buffersize (int, optional): [description]. Defaults to 20.
        retain (int, optional): [description]. Defaults to 5.
        raw_audio_dir (str, optional): [description]. Defaults to None.
        manifest_dir (str, optional): [description]. Defaults to None.

    Raises:
        e: [description]
        e: [description]
        e: [description]
    """

    manifest_dir = os.path.join(data_dir, "manifests")
    raw_audio_dir = os.path.join(data_dir, "raw_audio")
    raw_stream_dir = os.path.join(data_dir, "raw_stream")

    logging.info('Opening stream ...')
    audio_stream = AudioStream(url)
    audio_stream.save_manifest_file(manifest_dir)

    logging.info("Start ffmpeg subprocess...")

    # create directory but remove the temporary stream file
    raw_stream_dir = raw_stream_dir or "./data/raw_stream"
    os.makedirs(raw_stream_dir, exist_ok=True)
    if os.path.exists(audio_stream.raw_stream_file_path):
        os.remove(audio_stream.raw_stream_file_path)

    # start the subprocess for ffmpeg
    cmd = " ".join(
        [
            "ffmpeg", 
            "-i", str(audio_stream.url),
            "-f", "f32le",
            "-codec", "pcm_f32le",
            "-ac", str(audio_stream.channels),
            "-ar", str(audio_stream.samplerate),
            "-loglevel", "panic",
            "pipe: &>", audio_stream.raw_stream_file_path
        ]
    )
    logging.warning(f"... Execute {cmd}")
    process = subprocess.Popen(
        cmd, 
        shell=True
    )
    pid = process.pid

    # monitor the stream file get initiated
    while True:
        if os.path.exists(audio_stream.raw_stream_file_path):
            listener = open(audio_stream.raw_stream_file_path, mode="rb")
            break
    try:
        _stream_sample_size = 4 # The size in bytes of a single sample.
        read_size = blocksize * audio_stream.channels * _stream_sample_size
        logging.info(f'[{pid}] Starting Recording ...')
        capture_seq = b''
        retain_cnt = -1
        while True:
            metablock = listener.read(read_size)
            np_block = NumpyAudioFrame(np.frombuffer(metablock, dtype='float32'))
            np_block_info = np_block.__repr__()
            if np_block.retain == 1:
                retain_cnt = retain
            if retain_cnt > 0:
                if np_block.retain >= 0:
                    logging.info(f"[{pid}] Capture {np_block_info}, Fetch Next Frame ({retain_cnt})")
                    capture_seq += metablock
                    if np_block.dim[0] == blocksize:
                        retain_cnt -= 1
                    else:
                        logging.debug(f"[{pid}] Skip counting the incomplete frame, Fetch Next Frame ({retain_cnt})")
                else:
                    logging.debug(f"[{pid}] Skip counting, Fetch Next Frame ({retain_cnt})")
            elif retain_cnt == 0:
                time_str = datetime.datetime.now().strftime(format="%Y%m%d-%H%M%S")
                export_audio_path = os.path.join(raw_audio_dir, f"{audio_stream.flag}-{time_str}.raw")
                logging.warning(f"[{pid}] Export raw file to path: {export_audio_path}")
                with open(export_audio_path, mode="wb") as f:
                    f.write(capture_seq)
                retain_cnt -= 1
            else:
                capture_seq = b''
                retain_cnt = -1
    except KeyboardInterrupt:
        logging.info(f'[{pid}] Terminated due to Interrupted by user')
        sys.exit(0)
    except Exception as e:
        raise e

if __name__ == "__main__":

    URL="http://d.liveatc.net/kbos_twr"
    BLOCKSIZE=2048
    RETAIN=10
    DATA_DIR="./data"

    listen_main(URL, BLOCKSIZE, RETAIN, DATA_DIR)