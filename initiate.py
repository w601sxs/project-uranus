import os

def setup(data_dir, dry_run=False):

    if dry_run is True and os.path.exists(data_dir):
        try:
            os.system(f"rm -rf {os.path.abspath(data_dir)}")
        except Exception as e:
            print(f"Failed to clean up the data directory due to Exception {e}")

    dirs = {
        "manifest_dir": os.path.join(data_dir, "manifests"),
        "raw_audio_dir": os.path.join(data_dir, "raw_audio"),
        "clean_audio_dir": os.path.join(data_dir, "processed_audio"),
        "stream_info_dir": os.path.join(data_dir, "stream_info")
    }
    for directory in dirs.values():
        os.makedirs(directory, exist_ok=True)

    return