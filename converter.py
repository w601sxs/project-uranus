import pydub
import os

def deploy_converter_main(data_dir, min_silence_len=500, silence_thresh=-40, extend=10):
    
    raw_audio_dir = os.path.join(data_dir, "raw_audio")
    processed_audio_dir = os.path.join(data_dir, "processed_audio")
    
    raw_audio_names = [fpath for fpath in os.listdir(raw_audio_dir)]
    raw_audio_paths = [os.path.join(raw_audio_dir, fname) for fname in raw_audio_names]
    for raw_audio_name, raw_audio_path in zip(raw_audio_names, raw_audio_paths):
        raw_audio_file = pydub.AudioSegment.from_mp3(raw_audio_path)
        offset_lists = pydub.silence.detect_nonsilent(
            raw_audio_file,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh
        )
        for (start_offset, end_offset) in offset_lists:
            rec_start_offset = max(start_offset-extend, 0)
            rec_end_offset = min(end_offset+extend, len(raw_audio_file))
            chunk = raw_audio_file[rec_start_offset:rec_end_offset]
            offset_str = f"{rec_start_offset}-{rec_end_offset}"
            print(offset_str)
            export_filename = os.path.join(
                processed_audio_dir,
                raw_audio_name.replace(".mp3", f"-{offset_str}.mp3")
            )
            print(f"exported sound slice {export_filename}")
            chunk.export(export_filename, format="mp3")
