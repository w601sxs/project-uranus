from cProfile import run
#!/usr/local/bin/python

import os
import logging
import time

logging.basicConfig(
     level=logging.INFO, 
     format= '%(asctime)s > %(funcName)s:%(levelname)s >> %(message)s',
     datefmt='%Y-%m-%d %H:%M:%S %Z'
 )

if __name__ == "__main__":

    run_config = {
        "rerun": os.environ.get("RERUN", 120)
    }

    for k, v in run_config.items():
        if k in ["rerun"]:
            run_config[k] = int(v) if v is not None else None

    logging.warning(f"[db updator] placeholder update the database, rerun in {run_config['rerun']}s")
    time.sleep(run_config["rerun"])