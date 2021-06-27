import ffmpeg
import sys
import os
import subprocess
import json
import numpy as np
import logging
import time

logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] > %(filename)s:%(funcName)s >> %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S'
)
class NumpyAudioFrame(object):
    def __init__(self, frame_vector, prec=4):
        self.frame_vector = frame_vector
        self.dim = frame_vector.shape
        self.min = frame_vector.min()
        self.max = frame_vector.max()
        self.avg = frame_vector.mean()
        self.retain = (np.round(self.avg, prec) != 0)

    def __repr__(self):
        if self.retain == True:
            return "Frame --> Shape: {}, Avg: {:.3f}, Max: {:.3f}, Min: {:.3f}".format(self.dim, self.avg, self.max, self.min)
        else:
            return "Frame --> Shape: {}".format(self.dim)

class AudioStream(object):
    def __init__(self, url, raw_stream_file_path=None, fetch_ready=True):
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
            self.raw_stream_file_path = raw_stream_file_path or f"./data/raw_stream/{self.flag}.stream"
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
        
    def save_manifest_file(self, manifest_dir=None, manifest_name=None):
        manifest_dir = manifest_dir or "./data/manifests"
        manifest_name = manifest_name or f"{self.flag}.json"
        manifest_fpath = os.path.join(manifest_dir, manifest_name)
        logging.warning(f"Save Manifest File to {manifest_fpath}")
        os.makedirs(manifest_dir, exist_ok=True)
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
    raw_stream_dir = raw_stream_dir or "./data/raw_stream"
    os.makedirs(raw_stream_dir, exist_ok=True)
    cmd = " ".join(
        [
            "ffmpeg", 
            "-i", str(audio_stream.url),
            "-f", "f32le",
            "-codec", "pcm_f32le",
            "-ac", str(audio_stream.channels),
            "-ar", str(audio_stream.samplerate),
            "-loglevel", "panic",
            "pipe: | cat >", str(audio_stream.raw_stream_file_path)
        ]
    )
    logging.warning(f"... Execute {cmd}")
    # listener = subprocess.Popen(cmd, shell=True)

    try:
        _stream_sample_size = 4 # The size in bytes of a single sample.
        read_size = blocksize * audio_stream.channels * _stream_sample_size
        logging.info('Starting Recording ...')
        capture_seq = b''
        retain_cnt = -1
        while True:
            print("aaa")
            time.sleep(5)
            # metablock = listener.stdout.read(read_size)
            # np_block = NumpyAudioFrame(np.frombuffer(metablock, dtype='float32'))
            # np_block_info = np_block.__repr__()
            # if np_block.retain == True:
            #     retain_cnt = retain
            # if retain_cnt > 0:
            #     logging.info(f"Capture {np_block_info}, Fetch Next Frame ({retain_cnt})")
            #     capture_seq += metablock
            #     retain_cnt -= 1
            # elif retain_cnt == 0:
            #     time_str = datetime.datetime.now().strftime(format="%Y%m%d-%H%M%S")
            #     export_audio_path = os.path.join(raw_audio_dir, f"{audio_stream.flag}-{time_str}.raw")
            #     logging.warning(f"Export raw file to path: {export_audio_path}")
            #     with open(export_audio_path, mode="wb") as f:
            #         f.write(capture_seq)
            #     retain_cnt -= 1
            # else:
            #     capture_seq = b''
            #     retain_cnt = -1
    except KeyboardInterrupt:
        logging.info('Terminated due to Interrupted by user')
        sys.exit(0)
    except Exception as e:
        raise e

if __name__ == "__main__":

    URL="http://d.liveatc.net/kbos_twr"
    BLOCKSIZE=2048
    RETAIN=5
    DATA_DIR="./data"

    listen_main(URL, BLOCKSIZE, RETAIN, DATA_DIR)