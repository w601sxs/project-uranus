from lxml import etree
import os
import datetime
import pandas as pd
import json
import urllib.request as urlrequest

def get_flag(pls_link):
    return pls_link.strip("/play/").split(".")[0]

def flag_to_stream_link(flag):
    return "http://d.liveatc.net/{}".format(flag)

_url_dict = {
    "US-Class-B": "https://www.liveatc.net/feedindex.php?type=class-b",
    "US-Class-C": "https://www.liveatc.net/feedindex.php?type=class-c",
    "US-Class-D": "https://www.liveatc.net/feedindex.php?type=class-d",
    "US-ARTCC": "https://www.liveatc.net/feedindex.php?type=us-artcc",
    "International-EU": "https://www.liveatc.net/feedindex.php?type=international-eu",
    "CA": "https://www.liveatc.net/feedindex.php?type=canada",
    "International-AS": "https://www.liveatc.net/feedindex.php?type=international-as"
}

def crawl_stream_info(stream_info_export_path):
    stream_df_collection = {}
    print(f"Start Fetching Stream Information")
    for category, url in _url_dict.items():
        page = urlrequest.urlopen(url).read()
        print(f"Parsed URL: {url}")
        html = etree.HTML(page)
        available_href = [item.attrib["href"]
            for item in html.xpath("//table[@bgcolor='#EEEEEE']//td[@bgcolor='lightgreen']//a[contains(@href, '/play/')]")
        ]
        available_texts = [list(item.itertext()) 
            for item in html.xpath("//table[@bgcolor='#EEEEEE']//td[@bgcolor='lightgreen']")
        ]
        available_flags = [get_flag(pls_link) for pls_link in available_href]
        available_links = [flag_to_stream_link(flag) for flag in available_flags]
        available_abstract = [texts[0] for texts in available_texts]
        available_loc = [texts[2] for texts in available_texts]
        available_metar = [texts[11] for texts in available_texts]
        assert len(available_links) == len(available_texts)
        print(f"Fetched {len(available_links)} Links through URL: {url}")
        stream_info_df = [
            {"flag": flag, "stream_link": url, "abstract": abstract, "category": category, "metar": metar, "location": loc}
            for flag, url, abstract, metar, loc in zip(available_flags, available_links, available_abstract, available_metar, available_loc)
        ]
        stream_info_df = pd.DataFrame.from_records(stream_info_df)
        stream_info_df["fetch-time"] = datetime.datetime.utcnow().strftime(format="%Y-%m-%d %H:%M:%S UTC")

        # post process of metar to assure the metar information is correct
        stream_info_df.loc[
            stream_info_df["metar"].map(lambda x: x[:4].lower()) != stream_info_df["flag"].map(lambda x: x[:4].lower()),
            "metar"
        ] = None

        stream_info_df = stream_info_df.set_index("flag")
        stream_df_collection[category] = stream_info_df

    stream_final_df = pd.concat([meta_df for meta_df in stream_df_collection.values()])
    if stream_info_export_path is not None:
        os.makedirs(os.path.dirname(stream_info_export_path), exist_ok=True)
        print(f"Create/Update Stream Info to: {stream_info_export_path}")
        stream_final_df.to_json(stream_info_export_path, orient="records", indent=2)
        stream_final_dict = json.loads(stream_final_df.to_json(stream_info_export_path, orient="records", indent=2))
        return stream_final_dict
    else:
        return