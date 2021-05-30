import ffmpeg
import os
import sys
import time
import json
import logging

logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] > %(filename)s:%(funcName)s >> %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S'
 )

def meta_convert(input_fpath, output_fpath, channel, samplerate, format="f32le"):
    convert_process = ffmpeg.input(
        input_fpath, 
        ac=channel, 
        ar=samplerate, 
        format=format,
        loglevel='panic',
    ).output(
        output_fpath
    ).run()
    logging.info(f"Completed convert {input_fpath} >> {output_fpath}")

def convert_rawfile_main(manifest_dir, raw_audio_dir, export_audio_dir, hold_sec=3):
    manifest_dict_collection = {}
    for fname in os.listdir(manifest_dir):
        manifest_path = os.path.join(manifest_dir, fname)
        with open(manifest_path, mode="r") as f:
            manifest_dict = json.load(f)
        manifest_dict_collection[manifest_dict["flag"]] = manifest_dict
    logging.info(f"Acquired {len(manifest_dict_collection)} manifest files ...")
    logging.info("Start convert raw audio files")

    try:
        while True:
            remain_files = [
                fname for fname in os.listdir(raw_audio_dir) if ".raw" in fname
            ]
            if len(remain_files) == 0:
                time.sleep(hold_sec)
                logging.info(f"Converted process onhold {hold_sec}s")
            else:
                for fname in remain_files:
                    input_path = os.path.join(raw_audio_dir, fname)
                    output_path = os.path.join(
                        export_audio_dir, 
                        fname.replace(".raw", ".mp3")
                    )
                    input_flag = fname.split("-")[0]
                    meta_convert(
                        input_fpath=input_path,
                        output_fpath=output_path,
                        channel=manifest_dict_collection[input_flag]["channels"],
                        samplerate=manifest_dict_collection[input_flag]["samplerate"]
                    )
                    os.remove(input_path)
    except KeyboardInterrupt:
        logging.info('Terminated due to Interrupted by user')
        sys.exit(0)
    except Exception as e:
        raise e
    


if __name__ == "__main__":

    convert_rawfile_main(
        "./manifests",
        "./raw_audio",
        "./clean_audio"
    )

    # meta_convert(
    #     input_fpath="raw_audio/kbos_twr-20210530-165939.raw", 
    #     output_fpath="clean_audio/kbos_twr-20210530-165939.mp3", 
    #     channel=1, 
    #     samplerate=22150, 
    #     format="f32le"
    # )