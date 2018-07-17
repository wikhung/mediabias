import os
import csv
import logging
import datetime
import re
from bs4 import BeautifulSoup, NavigableString

# Set up the logger
logging.basicConfig(filename="parse.log",
                    filemode="a",
                    datefmt='%H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class HTMLParser(object):
    def __init__(self, data_path):
        self.data_path = data_path

        # Set up the meta data
        self.missing_title = 0
        self.missing_author = 0
        self.missing_genre = 0
        self.missing_article = 0

    def reset_counters(self):
        self.missing_title = 0
        self.missing_article = 0
        self.missing_genre = 0
        self.missing_author = 0

    def soup_opener(self, file_path, file_name):
        # open the html file and pass it to beautifulsoup
        with open(os.path.join(file_path, file_name), 'rb') as f:
            soup = BeautifulSoup(f, 'html.parser')

        return soup

    # Parse the filename as the publish time
    def parse_publishtime(self, file_name):
        return "-".join(file_name.split("_")[:3])

    def infowars_tags(self, tag):
        return (tag.name in ['td', 'div'] and len(tag.contents) >1  and tag.contents[1].name == 'span')

    def p_tag_with_only_string(self, tag):
        return (tag.name == "p" and not tag.find('input') and not tag.find('script') and isinstance(tag.next_element, NavigableString))

    def times_html_parser(self, file_path, file_name):
        soup = self.soup_opener(file_path, file_name)

        # Find the title and article tags by general descriptors
        title_tag = soup.find(class_=["artHd", "entry_title", "entryTitle", "entry-title"])
        article_tag = soup.find(class_=["artTxt", "entry_wrapper", "entryBody", "articleContent", "entry-content"])

        # If the general descriptors cannot find anything, use the id
        if not title_tag:
            title_tag = soup.find(id="articleWrap")
            article_tag = soup.find(id="articleCopy")

        # If the title is in h1 tag, it also contains the byline
        if title_tag.h1:
            title = title_tag.h1.get_text()
            byline = title_tag.find(class_="byline").get_text()
            byline = re.sub("[\n\t]", "", byline)
        else:
            title = title_tag.get_text()
            byline = None

        # Parse the byline if it is found
        if byline:
            byline_in_list = byline.split(" ")
            # Find the index of "by" and "By" to find the author name
            signal_word_pos = [i for i, word in enumerate(byline_in_list) if word in ["by", "By"]]

            # Because sometimes there are a few empty strings between the word By/by and author name,
            # loop through the words after signal word to see which one is not empty
            next_word_len = len(byline_in_list[signal_word_pos[0] + 1])
            while next_word_len == 0:
                signal_word_pos[0] += 1
                next_word_len = len(byline_in_list[signal_word_pos[0] + 1])

            # Find the author name by most updated index
            author = " ".join(byline.split(" ")[signal_word_pos[0] + 1: signal_word_pos[0]+3]).lower()
        else:
            author = ""
            self.missing_author += 1

        # Grab the article from the p tags in the article tag
        article = " ".join([p.get_text().strip() for p in article_tag.find_all("p")])

        # No genre in Times
        genre = ""
        self.missing_genre += 1

        return title, author, genre, article

    def infowars_html_parser(self, file_path, file_name):
        soup = self.soup_opener(file_path, file_name)

        # Remove all comments related elements from the soup
        tags = ["ol", "form", "div"]
        for tag in tags:
            params = {}
            params["name"] = tag
            if tag == "ol":
                params["class_"] = "commentlist"
            elif tag == "div":
                params["id"] = "respond"
            elif tag == "form":
                params["id"] = "commentform"

            for c in soup.find_all(**params):
                c.decompose()

        # Title
        title = soup.title.get_text()

        # Get the tag that contains the article
        text = soup.find(['td', 'div'], {"class": ["subheadline_body", "text", "subarticle"]})
        if file_name == "2007_03_14_IW.html":
            text = soup.find(self.infowars_tags, {"class": ["subheadline_body", "text", "subarticle"]})

        # Get the more precise tag from the text tag
        if text.attrs['class'][0] == "text":
            text = text.find("article")

        # TODO: Need to find a way to parse the author data from the text body
        author = ""
        self.missing_author += 1

        genre = ""
        self.missing_genre += 1

        article = "".join([p.get_text().strip() for p in text.find_all(self.p_tag_with_only_string, class_=False)])

        return title, author, genre, article

    def nyp_html_parser(self, file_path, file_name):
        soup = self.soup_opener(file_path, file_name)

        # Title
        try:
            # Try to get the title from the h1 tag. If h1 does not have the title, get it from the title tag instead.
            # However, it is important to note the title tag did not match the actual content in some cases.
            title = soup.h1.string
            if not title:
                title = soup.title.string
                title = title.split("-")[0]
        except:
            self.missing_title += 1
            title = ""

        # Author. Seems like author information is missing from all new york post articles.
        author = ""
        self.missing_author += 1

        # Genre
        try:
            genre = soup.find("li", {"class": "current"}).get_text()
        except AttributeError:
            self.missing_genre += 1
            genre = ""

        # Article
        # Find all p tags excluding date time entries
        paragraphs = soup.find_all('p', id=lambda x: x != "site_updated", class_=False)
        # Remove all p tags that contains a or span tags in child
        paragraphs = [p for p in paragraphs if not (p.find('a') or p.find('span'))]

        # Exclude a couple of lines that are able copyright and publication
        article = " ".join([p.get_text().strip() for p in paragraphs
                            if not ("NEW YORK POST" in p.get_text() or "Copyright" in p.get_text())])

        return title, author, genre, article

    # Parser for New York Times html files
    def nyt_html_parser(self, file_path, file_name):
        # open the html file and parse it with bs4
        soup = self.soup_opener(file_path, file_name)

        # save the title
        title = soup.title.string
        # strip the NYT name from the article title
        title = title.split("-")[0]

        # author of the article
        try:
            author = soup.find(class_="byline-author").string
        except AttributeError:
            self.missing_author += 1
            author = ""

        # Genre
        try:
            genre = soup.find(class_="story-meta").a.string
        except AttributeError:
            self.missing_genre += 1
            genre = ""

        # grab all the story paragraphs in the file as a list
        paragraphs = soup.find_all('p', class_='story-body-text story-content')
        # Check if article is missing
        if len(paragraphs) == 0:
            self.missing_article += 1

        # join all the paragraphs into one string
        article = " ".join([p.get_text().strip() for p in paragraphs])

        return title, author, genre, article

    # Parse the articles from provided Media Outlet
    def parse(self, media, csv_filename=None):
        """
        :param media: name of the media outlet
        :param csv_filename: csv file to be used to save the parsed data
        :return: None
        """

        # Reset the missing values counter
        self.reset_counters()

        # Structure of the data
        fieldnames = ["headline", "author", "genre", "content", "media", "datetime"]

        # Join the media to figure out the correct data path
        files_path = os.path.join(self.data_path, media)
        # Count the number of HTML files in the media outlet
        files = os.listdir(files_path)
        html_files = [file for file in files if ".html" in file]
        logger.info("There are a total of {} {} articles".format(len(html_files), media))

        # Find the appropriate parser for the media outlet
        if media == "New York Times":
            parser = self.nyt_html_parser
        elif media == "New York Post":
            parser = self.nyp_html_parser
        elif media == "InfoWars":
            parser = self.infowars_html_parser
        elif media == "Time Magazine":
            parser = self.times_html_parser

        if csv_filename:
            parsed_headlines = self.csv_reader(csv_filename, media)
            # Save the data if csv file path is provided
            csv_exist = os.path.isfile(csv_filename)
            csvfile = open(csv_filename, 'a', newline='')

            if not csv_exist:
                self.csv_writer(csvfile, csv_filename, fieldnames, csv_exist=csv_exist)

        # Loop through all the files
        for file in html_files:
            # parse the html files
            values = parser(files_path, file)
            # Datetime (Save the datetime format by YEAR-MONTH-DAY
            publish_time = self.parse_publishtime(file)
            # If headline and publish time are new, write it to the csv
            if csv_filename and parsed_headlines.get(publish_time) != values[0]:
                self.csv_writer(csvfile, csv_filename, fieldnames, values + (media, publish_time,))

        if csv_filename:
            csvfile.close()

        logger.info("No author information for {} articles".format(self.missing_author))
        logger.info("No genre information for {} articles".format(self.missing_genre))
        logger.info("No content for {} articles".format(self.missing_article))

    def csv_reader(self, csv_filename, media):
        try:
            with open(csv_filename, 'rt', encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                parsed_headlines = {row['datetime']: row['headline'] for row in reader if row['media'] == media}
        except FileNotFoundError:
            parsed_headlines = {}
            logger.info("datafile not created yet.")
        return parsed_headlines

    def csv_writer(self, f, csv_filename, fieldnames, values=None, csv_exist = True):
        """
        :param csv_filename: csv file to be written
        :param values: tuples of parsed html data
        :return: None
        """
        csvwriter = csv.DictWriter(f, fieldnames=fieldnames)
            # Write the header if the csv file doesn't exist
        if not csv_exist:
            csvwriter.writeheader()
        else:
            # Encode the data in UTF8 to avoid some character issues
            line = dict(zip(fieldnames, values))

            # Write all the rows in the data
            csvwriter.writerow(line)


if __name__ == "__main__":
    data_path = "data"
    logger.info("logging session: {}".format(datetime.datetime.now()))

    article_parser = HTMLParser(data_path)
    #article_parser.parse("New York Times", csv_filename='media_data.csv')
    #article_parser.parse("New York Post", csv_filename='media_data.csv')
    #article_parser.parse("InfoWars", csv_filename='media_data.csv')
    article_parser.parse("Time Magazine")
