from lxml import etree
import os
import sys
import pandas as pd
import logging
import urllib.request as urlrequest

logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] > %(filename)s:%(funcName)s >> %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S'
 )

_url_dict = {
    "US-Class-B": "https://www.liveatc.net/feedindex.php?type=class-b",
    "US-Class-C": "https://www.liveatc.net/feedindex.php?type=class-c",
    "US-Class-D": "https://www.liveatc.net/feedindex.php?type=class-d",
    "US-ARTCC": "https://www.liveatc.net/feedindex.php?type=us-artcc",
    "International-EU": "https://www.liveatc.net/feedindex.php?type=international-eu",
    "CA": "https://www.liveatc.net/feedindex.php?type=canada",
    "International-AS": "https://www.liveatc.net/feedindex.php?type=international-as"

}

def get_flag(pls_link):
    return pls_link.strip("/play/").split(".")[0]

def flag_to_stream_link(flag):
    return "http://d.liveatc.net/{}".format(flag)

def fetch_main(export_path=None):
    stream_df_collection = {}
    logging.info(f"Start Fetching Stream Information")
    for category, url in _url_dict.items():
        page = urlrequest.urlopen(url).read()
        logging.info(f"Parsed URL: {url}")
        html = etree.HTML(page)
        available_href = [item.attrib["href"]
            for item in html.xpath("//table[@bgcolor='#EEEEEE']//a[contains(@href, '/play/')]")
        ]
        available_flags = [get_flag(pls_link) for pls_link in available_href]
        available_links = [flag_to_stream_link(flag) for flag in available_flags]
        available_abstract = [item.text
            for item in html.xpath("//table[@bgcolor='#EEEEEE']//a[contains(@onclick, 'myDirectStream')]")
        ]
        assert len(available_links) == len(available_abstract)
        logging.info(f"Fetched {len(available_links)} Links through URL: {url}")
        stream_info_df = [{"flag": flag, "stream_link": url, "abstract": abstract, "category": category, "metar": None, "description": None} for flag, url, abstract in zip(available_flags, available_links, available_abstract)]
        stream_info_df = pd.DataFrame.from_records(stream_info_df).set_index("flag")
        stream_df_collection[category] = stream_info_df

    stream_final_df = pd.concat([meta_df for meta_df in stream_df_collection.values()])
    print(stream_final_df)
    if export_path is not None:
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        logging.info(f"Create/Update Stream Info to: {export_path}")
        stream_final_df.to_csv(export_path)

if __name__ == "__main__":
    fetch_main("./stream_info.csv")
