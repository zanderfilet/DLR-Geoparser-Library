# DLR-Geoparser-Library

![Sample Map using WGP](/preview/sample1.png "Sample Map using WGP")

The Website Geoparsing (WGP) library is a tool with which to perform large scale geoparsing tasks by crawling through a domain. With this library, you will be able to project location mentions from a domain on a world map (as shown above) in addition to other helpful tools. 
<br/><br/><br/>
# Features
<br/>
<img src="/preview/sample2.png" alt="Zoomed in" width="700"/>
<br/>
Using the Matplotlib interface, you can zoom into specific regions on the map, navigate easily, and save the map excerpt on your computer. 
<br/><br/><br/>
<img src="/preview/sample3.png" alt="Point information" width="700"/>
<br/><br/>
With the WGP library, you can select points on the interface to see the category this point belongs to, its exact address and coordinates, the original search query used for Nominatim, and the underlying URLs in the domain that reference this location. For each referencing URL, the frequency of this location is mentioned and the keywords on this website. 
<br/><br/><br/>
<img src="/preview/sample4.png" alt="Point trends" width="1000"/>
<br/><br/>
Using these features, certain trends in news reporting can be discovered. In this example, the two webpages that discuss India include the keyword "covid-19", suggesting a trend of recent news on India focussing on the covid-19 developments there. 

# Preparation

#### Requirements

1. Copy the folder 'website-geoparser' into your python's site-packages directory. While this may vary between operating systems and python versions, the correct directory may be: `/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/site-packages`.

2. Install all required packages with `python -m pip install -r requirements.txt`

#### In your Python file

3. Import the library from your python file with `from website_geoparser.website_geoparser import website_geoparser`

4. Use the library features easily by assigning it to a variable: `WGP = website_geoparser()`

# Components

#### WGP.verbose = False

By setting `WGP.verbose = True`, you will receive feedback from the library in the command line about which operations were successful / unsuccessful. <br/>

#### WGP.website_links(url)

This function is the heart of this library's ability to crawl through full domains. With the input URL, this function returns an array of **internal URLs linked on the input website**. This means that you can iteratively open and check the urls of each subsequently mentioned website from the domain to crawl and determine the full domain network that you can analyze. 

#### WGP.url2text(url)

This function lets you input a URL and it returns the **raw visible text** on that website as a string. <br/>

#### WGP.extract_keywords(text, keyword_length = 10)

Providing input text, this function returns the keywords, proper nouns, nouns, and adjectives, in the text using **Spacy's pretrained German natural language model**. That means that if you wish to use this function on websites of another language, you will need to manually change the language model used on **line 55 and 92 in website_geoparser.py**. 

The default amount of returned keywords is 10. <br/>

#### WGP.parse_location_entities(text)

Providing input text, this function returns an array of locations mentioned, also using Spacy. This function is _not_ perfect, but in general, wrongly interpreted tokens are picked up on by Nominatim in its location query search in the get_coords function. <br/>

#### WGP.get_coords(locations)

This function returns an array of addresses identified with their latitude and longitude coordinates based on an input of an array of locations (as strings). Additionally, its second return parameter returns an array of the text conversions from the input queries to the addresses. This is important for the map_coords function.<br/>

#### WGP.map_coords(lat_lon, loc_mentions_freq, loc_conversions, location_urls, url_keywords, save_plot = False, plot_filename = "output")

This is the big function, which lets you graph coordinates of addresses, but it takes various input parameters:

1. **lat_lon** is the array of address and their coordinates, returned from get_coords, first parameter. However, you can also manually define this array, like all others for this function. 

2. **loc_mentions_freq** is the frequency each location is mentioned at. You can use the counter function, as used in the sample usage file, to keep track of the frequency each location is mentioned. This function is important to define the size of each bubble on the map. 

3. **loc_conversions** is the second parameter output from get_coords, which tracks the address found by Nominatim for a given query. This is an important detail displayed for each point information, as it can be helpful to see whtehr a certain location mention is valid. For example, Spacy recognizes "covid-19" as a location and so does Nomitim, but this is not truly a location in the context it is used in. With the search query, you can know if a result was intentional from the texts analyzed. 

4. **location_urls** is a dictionary to track how frequenty each website refers to a website. This is in the format: `\{location : \[\{"url":url, "frequency": location_term_frequency_for_url}, \{"url":url2, "frequency": location_term_frequency_for_url2}], ...}`. Refer to the sample usage file to see how this can be set up.

5. **url_keywords** is a dictionary which tracks the keywords for each url's text in the format: `\{url : \[keyword1, keyword2, ...]}`.

6. **save_plot and plot_filename**. By default, `map_coords()` function will not save the plot for you, but you can set it to do so by setting the parameter `save_plot = True`. You can also manually set the filename instead of the default "output" with `plot_filename = your_filename`.

#### WGP.url2text(url)

This function lets you input a URL and it returns the **raw visible text** on that website as a string. <br/>

# General Setup

To fully crawl and geoparse a domain, all these functions work in harmony with one another.

You can crawl a whole domain by defining the base url and using the `website_links()` function recursively for all the URLs it finds, until there are no more internal URLs. Then, you can read the text of each website to extract the keywords and location mentions using `extract_keywords()` and `parse_location_entities()`. Lastly, you can get the coordinates of each location with `get_coords()`. With some small rearranging of the data, you can then plot all of these locations and start your visual analysis!

# Performance Issues

- This library takes a while to load its libraries and, most significantly, get the coordinates using Nominatim's API. 

- If this project is required on a large scale, I would recommend downloading the full 900GB Nominatim OSM database for much better performance. 

- Additionally, if there are a lot of points plotted, using the matplotlib interface can become quite slow. Therefore, I recommend using the crawling functionality sparingly. For example, the sample does not develop a crawler either and only uses the first n URLs mentioned in the root URL text.



