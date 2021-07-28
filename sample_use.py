from web_geo_library.website_geoparser import website_geoparser
from collections import Counter
from tqdm import tqdm

web_geo = website_geoparser()

web_geo.verbose = True

#Find websites on root page
links = list(web_geo.website_links("https://sz.de"))[:15]

total_locs = []
location_urls = {}
url_keywords = {}

for link in tqdm(links): # Open each website found on the root page through

    # Get each website text, process it, extract keywords
    text = web_geo.url2text(link)
    kw = web_geo.extract_keywords(text, keyword_length=6) # Set keyword quantity to 4
    url_keywords[link] = kw

    # Find location mentions
    locations_index, locations = web_geo.parse_location_entities(text)
    lc_loc = [loc.lower() for loc in locations]
    unq_locs = Counter(lc_loc)

    # Save location mentions attributed to each URL + frequency
    for location, frequency in unq_locs.items():
        if location in location_urls:
            location_urls[location].append({"url":link, "frequency":frequency})
        else:
            location_urls[location] = [{"url":link, "frequency":frequency}]

    total_locs.extend(lc_loc)

unique_locs = Counter(total_locs)

# Get coordinates of all locations + the names of addresses found
lat_lon, loc_conv = web_geo.get_coords(unique_locs.keys())

# Load map
web_geo.map_coords(lat_lon, unique_locs, loc_conv, location_urls, url_keywords)

