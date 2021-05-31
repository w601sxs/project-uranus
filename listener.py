import ffmpeg
import sys
import os
import datetime
import sounddevice as sd
import json
import numpy as np
import logging

logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] > %(filename)s:%(funcName)s >> %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S'
 )

class AudioInfo(object):
    def __init__(self, url, stream, channels, samplerate):
        self.flag = url.split("/")[-1]
        self.url = url
        self.stream_codec_name = stream["codec_long_name"]
        self.channels = channels
        self.samplerate = samplerate
        self.stream = stream

    def save(self, manifest_dir="./", manifest_name=None):
        manifest_name = manifest_name or f"{self.flag}.json"
        manifest_fpath = os.path.join(manifest_dir, manifest_name)
        with open(manifest_fpath, mode="w") as f:
            json.dump(self.__dict__, f, indent=2)
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

def fetch_audio_info(url):
    """generate the audio information manifest for the target atc stream"""

    logging.info('Getting stream information ...')
    try:
        info = ffmpeg.probe(url)
    except ffmpeg.Error as e:
        sys.stderr.buffer.write(e.stderr)
        logging.info("Terminating due to: ffmpeg issue")

    streams = info.get('streams', [])
    assert len(streams) == 1, \
        'Ternimated due to: There must be exactly one stream available'
    stream = streams[0]
    assert stream.get('codec_type') == 'audio', \
        'Ternimated due to: The stream must be an audio stream'
    channels = stream['channels']
    samplerate = float(stream['sample_rate'])
    fetched_metainfo = {
        "url": url,
        "stream": stream["codec_long_name"],
        "channels": channels,
        "samplerate": samplerate
    }
    logging.info(f"Fetched Information: {json.dumps(fetched_metainfo, indent=2)}")
    return AudioInfo(url, stream, channels, samplerate)

def listener_main(url:str, blocksize:int=1024, retain:int=5, 
                  raw_audio_dir:str=None, manifest_dir:str=None):
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

    raw_audio_dir = raw_audio_dir or "./raw_audio"
    manifest_dir = manifest_dir or "./manifests"
    os.makedirs(raw_audio_dir, exist_ok=True)
    os.makedirs(manifest_dir, exist_ok=True)

    logging.info('Opening stream ...')
    metainfo = fetch_audio_info(url)
    metainfo.save(manifest_dir=manifest_dir)

    try:
        ffmpeg_listen_process = ffmpeg.input(
            metainfo.url
        ).output(
            'pipe:.mp3',
            format='f32le', # float 32 bit input
            acodec='pcm_f32le',
            ac=metainfo.channels, # 1 channel only
            ar=metainfo.samplerate, # given sample rate
            loglevel='panic',
        ).run_async(pipe_stdout=True)
        _stream_sample_size = 4 # The size in bytes of a single sample.

        read_size = blocksize * metainfo.channels * _stream_sample_size
        logging.info('Starting Recording ...')
        capture_seq = b''
        retain_cnt = -1
        while True:
            metablock = ffmpeg_listen_process.stdout.read(read_size)
            np_block = NumpyAudioFrame(np.frombuffer(metablock, dtype='float32'))
            np_block_info = np_block.__repr__()
            if np_block.retain == True:
                retain_cnt = retain
            if retain_cnt > 0:
                logging.info(f"Capture {np_block_info}, Fetch Next Frame ({retain_cnt})")
                capture_seq += metablock
                retain_cnt -= 1
            elif retain_cnt == 0:
                time_str = datetime.datetime.now().strftime(format="%Y%m%d-%H%M%S")
                export_audio_path = os.path.join(raw_audio_dir, f"{metainfo.flag}-{time_str}.raw")
                logging.warning(f"Export raw file to path: {export_audio_path}")
                with open(export_audio_path, mode="wb") as f:
                    f.write(capture_seq)
                retain_cnt -= 1
            else:
                capture_seq = b''
                retain_cnt = -1
    except KeyboardInterrupt:
        logging.info('Terminated due to Interrupted by user')
        sys.exit(0)
    except Exception as e:
        raise e

if __name__ == "__main__":

    URL="http://d.liveatc.net/kbos_twr"
    BLOCKSIZE=2048
    RETAIN=5
    EXPORT_DIR="./raw_audio"

    listener_main(URL, BLOCKSIZE, RETAIN, EXPORT_DIR)