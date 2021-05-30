import ffmpeg
import queue
import sys
import sounddevice as sd
import json

class AudioInfo(object):
    def __init__(self, url, stream, channels, samplerate):
        self.url = url
        self.stream_codec_name = stream["codec_long_name"]
        self.channels = channels
        self.samplerate = samplerate
        self.stream = stream

def fetch_audio_info(url):

    print('Getting stream information ...')
    try:
        info = ffmpeg.probe(url)
    except ffmpeg.Error as e:
        sys.stderr.buffer.write(e.stderr)
        print("Terminating due to: ffmpeg issue")

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
    print(f"Fetched Information: {json.dumps(fetched_metainfo, indent=2)}")
    return AudioInfo(url, stream, channels, samplerate)

def callback(outdata, frames, time, status):
    global q
    if status.output_underflow:
        print(f'Output underflow: increase blocksize? (Current: {frames})')
        raise sd.CallbackAbort
    assert not status
    try:
        data = q.get_nowait()
    except queue.Empty as e:
        print(f'Buffer is empty: increase buffersize? (Current: {q.maxsize})')
        raise sd.CallbackAbort from e
    assert len(data) == len(outdata)
    outdata[:] = data

def listener_main(url, device=None, blocksize=1024, buffersize=20):

    print('Opening stream ...')
    global q
    q = queue.Queue(maxsize=buffersize)
    metainfo = fetch_audio_info(url)

    try:
        process = ffmpeg.input(
            metainfo.url
        ).output(
            'pipe:',
            format='f32le',
            acodec='pcm_f32le',
            ac=metainfo.channels,
            ar=metainfo.samplerate,
            # loglevel='quiet',
        ).run_async(pipe_stdout=True)
        stream = sd.RawOutputStream(
            samplerate=metainfo.samplerate, blocksize=blocksize,
            device=device, channels=metainfo.channels, dtype='float32',
            callback=callback)
        read_size = blocksize * metainfo.channels * stream.samplesize
        print('Buffering ...')
        for _ in range(buffersize):
            metablock = process.stdout.read(read_size)
            q.put_nowait(metablock)
        print('Starting Playback ...')
        with stream:
            timeout = blocksize * buffersize / metainfo.samplerate
            while True:
                metablock = process.stdout.read(read_size)
                q.put(metablock, timeout=timeout)
    except KeyboardInterrupt:
        print('Terminated due to Interrupted by user')
        sys.exit(1)
    except queue.Full:
        # A timeout occurred, i.e. there was an error in the callback
        print("Termindated due to error in CallBack")
        sys.exit(1)
    except Exception as e:
        raise e

if __name__ == "__main__":

    URL="http://d.liveatc.net/kbos_twr"
    DEVICE=2
    BLOCKSIZE=1024
    BUFFERSIZE=20

    listener_main(URL, DEVICE, BLOCKSIZE, BUFFERSIZE)

    # >>> import sounddevice as sd
    # >>> sd.query_devices()
    # 0 LG HDR QHD, Core Audio (0 in, 2 out)
    # > 1 MacBook Pro Microphone, Core Audio (1 in, 0 out)
    # < 2 MacBook Pro Speakers, Core Audio (0 in, 2 out)