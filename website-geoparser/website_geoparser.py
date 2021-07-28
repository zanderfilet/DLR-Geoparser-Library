import spacy, urllib.request, html2text, nltk, re, time
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import geopandas as gpd
from geotext import GeoText
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from shapely.geometry import Point, Polygon
import descartes
from tqdm import tqdm
from string import punctuation
from collections import Counter
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from bs4.element import Comment

print("[WGP] Loaded Libraries.\n")

class website_geoparser:

    verbose = False

    def tag_visible(self, element):
        if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
            return False
        if isinstance(element, Comment):
            return False
        return True

    def html2text(self, body):
        soup = BeautifulSoup(body, 'html.parser')
        texts = soup.findAll(text=True)
        visible_texts = filter(self.tag_visible, texts)
        return u" ".join(t.strip() for t in visible_texts)

    def url2text(self, url):  # URL Request with urllib, HTML converted to text with html2text
        try:
            html = urllib.request.urlopen(url).read()
            if self.verbose: print("[WGP] Read HTML: Success.")

            text = self.html2text(html)
            token_words = nltk.word_tokenize(text)
            processed_text = " ".join(token_words)
            if self.verbose: print("[WGP] Convert HTML2Text: Success.\n")

            return processed_text
        except: # HTML Error
            if self.verbose: print("[WGP] Read HTML: FAILED. Returning empty string\n")
            return ""

    def extract_keywords(self, text, special_tags: list = None, keyword_length = 10): # Identify keywords in text based on frequency of proper nouns, nouns, adjectives

        nlp = spacy.load("de_core_news_sm") # Extract and count keywords using Spacy german language model

        result = []
        pos_tag = ['PROPN', 'NOUN', 'ADJ']

        doc = nlp(text.lower())

        if special_tags:
            tags = [tag.lower() for tag in special_tags]
            for token in doc:
                if token.text in tags:
                    result.append(token.text)

        for chunk in doc.noun_chunks:
            final_chunk = ""
            for token in chunk:
                if (token.pos_ in pos_tag):
                    final_chunk = final_chunk + token.text + " "
            if final_chunk:
                result.append(final_chunk.strip())

        for token in doc:
            if (token.text in nlp.Defaults.stop_words or token.text in punctuation):
                continue
            if (token.pos_ in pos_tag):
                result.append(token.text)
        if self.verbose: print("[WGP] Extract keywords: Success.")

        tf = Counter(result) # Process result to return top n items
        tf_sorted = {k: v for k, v in sorted(tf.items(), key=lambda item: item[1])}
        tf_main_kw = list(tf_sorted.keys())[len(list(tf_sorted.keys())) - keyword_length:]
        tf_final = list(reversed(tf_main_kw))
        if self.verbose: print("[WGP] Sort keywords: Success.\n")

        return tf_final

    def parse_location_entities(self, text):  # Spacy extract location mentions
        nlp = spacy.load("de_core_news_sm")
        doc = nlp(text)

        # get all elements under label "LOC" from Spacy NER: Note start and end point if desired (not applicable feature is available for this on WGP)
        location_mentions = [[(ent.text, ent.start, ent.end) for ent in doc.ents if ent.label_ == "LOC"], [ent.text for ent in doc.ents if ent.label_ == "LOC" ]]
        if self.verbose: print("[WGP] Location mentions extraction: Success. Found {} location mentions. {} of these are unique.\n".format(len(location_mentions[1]), len(list(set(location_mentions[1])))))

        return location_mentions

    def get_coords(self, locations): # Using Nominatim, get coordinates for location mentions, interpret as query

        geolocator = Nominatim(timeout=2, user_agent="DLR-geocoder-test")

        lat_lon = []
        loc_conv = {}

        success = []
        failed = []
        for loc in tqdm(locations):
            try:

                location = geolocator.geocode(loc)  # Nominatim URL Request: Takes a long time (~ 2 Requests / Min): Full OSM database can be downloaded (for faster performance) on:
                                                    # https://nominatim.org/release-docs/latest/admin/Installation/
                                                    # Database is 900 GB of hard drive space for the full earth

                if location:
                    if self.verbose: print("[WGP] Nominatim call: Success.")

                    loc_conv[location[0]] = loc
                    loc = location[0]

                    sizes = ["Land", "Bundesland", "Ort", "Bezirk", "Stadtteil", "Bezirksteil"]
                    parts = loc.split(",")
                    if len(parts) <= 6:
                        if len(parts) == 3:
                            if any(char.isdigit() for char in parts[1]):
                                lat_lon.append([location[0], location[1], "Postleitzahl"])
                            else:
                                lat_lon.append([location[0], location[1], "Ort"])
                        else:
                            lat_lon.append([location[0], location[1], sizes[len(parts) - 1]])
                    elif any(char.isdigit() for char in parts[0]):
                        lat_lon.append([location[0], location[1], "Addresse"])
                    elif "straße" in parts[0].lower():
                        lat_lon.append([location[0], location[1], "Straße"])
                    else:
                        lat_lon.append([location[0], location[1], "Standort"])
                    success.append(loc)
                    if self.verbose: print("[WGP] Result classification: Success.")

                else:
                    failed.append(loc)
                    if self.verbose: print("[WGP] Nominatim call: FAILED. Check query: {}".format(loc))

            except GeocoderTimedOut:
                print("[WGP] Nominatim Timed Out. Query: {}".format(loc))

        if self.verbose:
            print("[WGP] Get coordinates: Success. {} locations identified.\n".format(len(lat_lon)))
            suc = " ".join(success)
            fail = " ".join(failed)
            print("[WGP] Successes include: {}\n".format(suc))
            print("[WGP] Fails include: {}\n".format(fail))

        return [lat_lon, loc_conv]

    def map_coords(self, lat_lon, loc_mentions_freq, loc_conversions, location_urls, url_keywords, crs={'init': 'epsg:4326'}, save_plot = False, plot_filename = "output"): # Produce map with coordinates plotted
        pd_df = pd.DataFrame(lat_lon, columns=['Ort', 'Koordinaten', 'Typ'])
        def onclick(event): # Handle plot click events by selecting nearest neighbor: Identify nearest point and show information for this point
            if self.verbose: print("[WGP] Click Identified at x: {} y: {}".format(event.xdata, event.ydata))
            closeness = 50000
            option = ""
            for i in range(len(pd_df.index)):
                cn = (pd_df["Koordinaten"][i][0]-event.ydata)**2 + (pd_df["Koordinaten"][i][1]-event.xdata) ** 2
                if cn < closeness:
                    closeness = cn
                    option = i
            legend_df = pd.DataFrame(list(zip(["Legende_Keys"], [(0.0000, 0.0000)])),
                                    columns=['Ort', 'Koordinaten'])
            legend_geo = [Point(x[1], x[0]) for x in legend_df['Koordinaten']]
            legend_geo_df = gpd.GeoDataFrame(legend_df, crs=crs, geometry=legend_geo)
            legend_geo_df.plot(ax=ax, markersize=1, color="#ff0000", marker='o', alpha=1)
            nominatim_query = loc_conversions[pd_df["Ort"][option]]
            mentioned_in = location_urls[nominatim_query]
            URL_text = ""
            for URL_mention in mentioned_in:
                url = URL_mention["url"]
                kw = url_keywords[url]
                kw_string = ", ".join(kw)
                URL_text = "{}\n\{} ({}). Keywords: {}.".format(URL_text, url, URL_mention["frequency"], kw_string)
            plt.text(0, -0.15, "[{}] {}  {}                                                                                                                                                                   \nNominatim Query: {}\nMentioned in: {}".format(pd_df["Typ"][option], pd_df["Ort"][option], str(pd_df["Koordinaten"][option]), nominatim_query, URL_text),
                    verticalalignment='bottom', horizontalalignment='left',
                    transform=ax.transAxes,
                    color='black', fontsize=9, bbox={'facecolor': 'white', 'alpha': 1, 'pad': 10, 'edgecolor':'white'})
            if self.verbose: print("[WGP] Find nearest plot: Success. Showing info for location: {}\n".format(pd_df["Ort"][option]))


        geometry = [Point(x[1], x[0]) for x in pd_df['Koordinaten']]
        geo_df = gpd.GeoDataFrame(pd_df, crs=crs, geometry=geometry)
        f, ax = plt.subplots()

        # Load Shapely file into plot
        countries_map = gpd.read_file('./web_geo_library/ne_10m_admin_0_countries.shp')
        countries_map.plot(ax=ax, alpha=1,
                           color='grey')

        # Additional graph setup
        plt.xlabel("Breitengrad (W:-, O:+)")
        plt.ylabel("Längengrad (N:+, S:-)")
        if self.verbose: print("[WGP] Set up graph details: Success.")

        # Set up legend labels (manually for consistency)
        legend_df = pd.DataFrame(list(zip(["Legende_Keys"], [(90.0000,175.0000)])), columns=['Ort', 'Koordinaten'])
        legend_geo = [Point(x[1], x[0]) for x in legend_df['Koordinaten']]
        legend_geo_df = gpd.GeoDataFrame(legend_df, crs=crs, geometry=legend_geo)
        sizes = ["Land", "Bundesland", "Ort", "Bezirk", "Stadtteil", "Bezirksteil", "Postleitzahl", "Addresse", "Straße",
                 "Standort"]
        colors = ["#ff0000", "#00ff00", "#0000ff", "#ff00ff", "#ffff00", "#00ffff", "#999900", "#000000", "#990099", "#ff9900"]
        mk_s = [1, 2, 4, 8, 16]
        legend_geo_df.plot(ax=ax, markersize=1, color="#ffffff", marker='o', alpha=0, label=" ")
        for i in range(len(sizes)):
            legend_geo_df.plot(ax=ax, markersize=10, color=colors[i], marker='o', alpha=1, label=sizes[i])
        plt.legend(prop={'size': 7}, title='Legende', bbox_to_anchor=(1.01, 1), loc='upper left')
        legend_geo_df.plot(ax=ax, markersize=1, color="#ffffff", marker='o', alpha=0, label=" ")
        legend_geo_df.plot(ax=ax, markersize=1, color="#ffffff", marker='o', alpha=0, label="Größe:Freq")

        for i in range(len(mk_s)):
            legend_geo_df.plot(ax=ax, markersize=5 + (mk_s[i] - 1) * 5, color="g", marker='o', alpha=1, label=str(mk_s[i]))
        plt.legend(prop={'size': 10}, title='Legende', bbox_to_anchor=(0.95, 1.01), loc='upper left')
        legend_geo_df.plot(ax=ax, markersize=81, color="#ffffff", marker='o', alpha=1)
        if self.verbose: print("[WGP] Load legend: Success.")

        # Plot each point individually for individual color / size options in-line with legend
        for loc_i in range(len(geo_df["geometry"])):
            loc_df = pd.DataFrame([lat_lon[loc_i]], columns=['Ort', 'Koordinaten', 'Typ'])
            loc_geo = [Point(x[1], x[0]) for x in loc_df['Koordinaten']]
            loc_geo_df = gpd.GeoDataFrame(loc_df, crs=crs, geometry=loc_geo)

            colorchart = {"Land": "#ff0000", "Bundesland": "#00ff00", "Ort": "#0000ff", "Bezirk": "#ff00ff", "Stadtteil": "#ffff00", "Bezirksteil": "#00ffff", "Postleitzahl":"#999900", "Addresse": "#000000", "Straße":"#990099", "Standort":"#ff9900"}

            color = colorchart[lat_lon[loc_i][2]]

            original_name = loc_conversions[lat_lon[loc_i][0]]
            no_mentions = loc_mentions_freq[original_name]

            mk_size = 5 + (no_mentions - 1) * 5

            loc_geo_df.plot(ax=ax, markersize=mk_size, color=color, marker='o', alpha=1)

        if self.verbose: print("[WGP] Plot all locations: Success.")

        cid = f.canvas.mpl_connect('button_press_event', onclick)

        plt.text(0, -0.15, " ",
                 verticalalignment='bottom', horizontalalignment='left',
                 transform=ax.transAxes,
                 color='black', fontsize=9, bbox={'facecolor': 'white', 'alpha': 1, 'pad': 10, 'edgecolor': 'white'})

        if save_plot:
            plt.savefig('{}.png'.format(plot_filename))
            if self.verbose: print("[WGP] Save plot: Success. Saved in local directory '/' with filename {}.png".format(plot_filename))
        if self.verbose: print("[WGP] Showing plot.\n")

        plt.show()

    def is_valid(self, url):  # Checks if URL is valid
        parsed = urlparse(url)
        if self.verbose: print("[WGP] URL ({}) valid: {}.\n".format(url, bool(parsed.netloc) and bool(parsed.scheme)))
        return bool(parsed.netloc) and bool(parsed.scheme)

    def website_links(self, url):  # Finds all URLs mentioned on a website (applicable for recursion)

        urls = set()
        domain_name = urlparse(url).netloc
        soup = BeautifulSoup(requests.get(url).content, "html.parser")

        internal_urls = set()
        external_urls = set()

        for a_tag in soup.findAll("a"):
            href = a_tag.attrs.get("href")
            if href == "" or href is None:
                continue

            href = urljoin(url, href)

            parsed_href = urlparse(href)
            href = parsed_href.scheme + "://" + parsed_href.netloc + parsed_href.path

            if not self.is_valid(href):
                continue
            if href in internal_urls:  # Already added
                continue
            if domain_name not in href:  # External link
                if href not in external_urls:
                    urls.add(href)
                    external_urls.add(href)
                continue
            urls.add(href)
            internal_urls.add(href)

        if self.verbose: print("[WGP] Get URLs: Success. Found {} unique entries.\n".format(len(list(urls))))

        return urls