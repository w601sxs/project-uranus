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
    return

def acquire_manifest_files(manifest_dir):
    manifest_dict_collection = {}
    for fname in os.listdir(manifest_dir):
        manifest_path = os.path.join(manifest_dir, fname)
        with open(manifest_path, mode="r") as f:
            manifest_dict = json.load(f)
        manifest_dict_collection[manifest_dict["flag"]] = manifest_dict

    return manifest_dict_collection

def convert_rawfiles(manifest_dict_collection, convert_fname_list, raw_audio_dir, export_audio_dir, expected_format=".mp3"):
    
    logging.info("Start convert raw audio files ...")
    for fname in convert_fname_list:
        input_path = os.path.join(raw_audio_dir, fname)
        output_path = os.path.join(
            export_audio_dir, 
            fname.replace(".raw", expected_format)
        )
        input_flag = fname.split("-")[0]
        meta_convert(
            input_fpath=input_path,
            output_fpath=output_path,
            channel=manifest_dict_collection[input_flag]["channels"],
            samplerate=manifest_dict_collection[input_flag]["samplerate"]
        )
        os.remove(input_path)
    return

def convert_rawfile_main(manifest_dir, raw_audio_dir, export_audio_dir, hold_sec=3, expected_format=".mp3"):
    try:
        while True:
            manifest_dict_collection = acquire_manifest_files(manifest_dir)
            if len(manifest_dict_collection) > 0:
                convert_fnamelist = [
                    fname for fname in os.listdir(raw_audio_dir) if ".raw" in fname
                ]
                if len(convert_fnamelist) > 0:
                    convert_rawfiles(
                        manifest_dict_collection, 
                        convert_fnamelist, 
                        raw_audio_dir, 
                        export_audio_dir, 
                        expected_format
                    )
                    logging.info(f"Next round of converting in {hold_sec} second(s) ...")
                else:
                    logging.info(f"No raw files found, recheck in {hold_sec} second(s)...")
                time.sleep(hold_sec)
    except Exception as e:
        logging.error("Convert process terminated due to Exception...")
        raise e


    


if __name__ == "__main__":

    convert_rawfile_main(
        "./data/manifests",
        "./data/raw_audio",
        "./data/clean_audio"
    )

    # meta_convert(
    #     input_fpath="raw_audio/kbos_twr-20210530-165939.raw", 
    #     output_fpath="clean_audio/kbos_twr-20210530-165939.mp3", 
    #     channel=1, 
    #     samplerate=22150, 
    #     format="f32le"
    # )