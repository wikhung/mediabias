import os
import datetime
import csv
import logging
from bs4 import BeautifulSoup

# Set up the logger
logging.basicConfig(filename="parse.log",
                    filemode="a",
                    datefmt='%H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

class HTMLParser(object):
    def __init__(self, data_path):
        self.data_path = data_path

        # Set up the meta data variables
        self.missing_author = 0
        self.missing_genre = 0
        self.missing_article = 0

    # Parser for New York Times html files
    def nyt_html_parser(self, file_path, file_name):
        # open the html file and parse it with bs4
        with open(os.path.join(file_path, file_name), 'rb') as f:
            soup = BeautifulSoup(f, 'html.parser')

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

        # Datetime (Save the datetime format by YEAR-MONTH-DAY
        publish_time = "-".join(file_name.split("_")[:3])

        # grab all the story paragraphs in the file as a list
        paragraphs = soup.find_all('p', class_='story-body-text story-content')
        # Check if article is missing
        if len(paragraphs) == 0:
            self.missing_article += 1

        # join all the paragraphs into one string
        article = " ".join([p.get_text() for p in paragraphs])

        return title, author, genre, publish_time, article

    # Parse the articles from provided Media Outlet
    def parse(self, media, csv_filename = None):
        """
        :param media: name of the media outlet
        :param csv_filename: csv file to be used to save the parsed data
        :return: None
        """
        # Join the media to figure out the correct data path
        files_path = os.path.join(self.data_path, media)
        # Count the number of HTML files in the media outlet
        files = os.listdir(files_path)
        html_files = [file for file in files if ".html" in file]
        logger.info("There are a total of {} {} articles".format(len(html_files), media))

        # Find the appropriate parser for the media outlet
        if media == "New York Times":
            parser = self.nyt_html_parser

        # Loop through all the files
        for file in html_files:
            values = parser(files_path, file)
            # Save the data if csv file path is provided
            if csv_filename:
                self.csv_writer(csv_filename, values + (media,))

        logger.info("No author information for {} articles".format(self.missing_author))
        logger.info("No genre information for {} articles".format(self.missing_genre))
        logger.info("No content for {} articles".format(self.missing_article))

    def csv_writer(self, csv_filename, values):
        """
        :param csv_filename: csv file to be written
        :param values: tuples of parsed html data
        :return: None
        """
        # Check if the csv file already exist
        file_exist = os.path.isfile(csv_filename)

        with open(csv_filename, 'a', newline = '') as csvfile:
            # Structure of the data
            fieldnames = ["headline", "author", "genre", "datetime", "content", "media"]

            csvwriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
            # Write the header if the csv file doesn't exist
            if not file_exist:
                csvwriter.writeheader()

            # Encode the data in UTF8 to avoid some character issues
            line = {k:v.encode("utf8") for k, v in dict(zip(fieldnames, values)).items()}
            # Write all the rows in the data
            csvwriter.writerow(line)

if __name__ == "__main__":
    #pass
    data_path = "data"
    logger.info("logging session: {}".format(datetime.datetime.now()))

    article_parser = HTMLParser(data_path)
    article_parser.parse("New York Times", csv_filename="nyt_data.csv")
    #title, article = nyt_parser('2007_01_18_NYT.html')
    #print(title)
    #print('\n')
    #print(article)
    #print(os.listdir("./data/New York Times"))

    # nyt_path = os.path.join(data_path, "New York Times")
    # files = os.listdir(nyt_path)
    # html_files = [file for file in files if ".html" in file]
    # print("There are a total of {} NYT articles".format(len(html_files)))
    #
    # classes = []
    # # open the html file and parse it with bs4
    # for file in html_files:
    #     with open(os.path.join(nyt_path, file), 'rb') as f:
    #         soup = BeautifulSoup(f, 'html.parser')
    #
    #         page_classes = [value for element in soup.find_all(class_ = True) for value in element['class']]
    #         print(soup.find(class_='title'))
    #     classes.extend(page_classes)
    #
    # print([v for v in set(classes) if "title" in v])