import os
import requests
import sqlite3
from bs4 import BeautifulSoup
from time import sleep, strptime
import random

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time

# constants
START_DATE = strptime('2024-12-01','%Y-%m-%d')
URLS = {'movies': 'https://letterboxd.com/_branzino/list/oscars-2026/',
        'oscars':'https://letterboxd.com/000_leo/list/oscars-2026-1/'}
AWARD_NUM = {'oscars':10}
USERS = [
        ('BC', '_branzino'),
         ('CA', 'honeydijon2'),
         ('DN', 'nbditsd'),
         ('KH', 'shewasak8rgrl'),
         ('MF', 'mfrye'),
         ('MT', 'michelletreiber'),
         ('NB', 'NikkiBerry'),
         ('RZ', 'BOBBY_ZEE'),
         ('TA', 'tarias')
         ]

scraped = 0


# Setup Chrome WebDriver
options = webdriver.ChromeOptions()
#options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
# Add a User-Agent to mimic a real browser
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

def initialize_tables(cur):
    '''creates database tables if not already existing'''

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
                    initials    char(2) PRIMARY KEY,
                    "user"      varchar(20)
                );''')

    cur.execute('''CREATE TABLE IF NOT EXISTS ratings (
                    initials    char(2),
                    filmid      integer, 
                    "date"      date,
                    rating      decimal,
                    PRIMARY KEY (filmid, initials)
                );''')

    cur.execute('''CREATE TABLE IF NOT EXISTS movies (
                    filmid      integer PRIMARY KEY,
                    slug        varchar(40),
                    title       varchar(40),
                    record      integer
                );''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS oscars (
                    filmid      integer PRIMARY KEY,
                    slug        varchar(40),
                    title       varchar(40),
                    record      integer
                );''')


def scrape(url):
    '''returns web scraping'''
    driver.get(url)

    try:
        # Wait for the page content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "film-poster"))
        )
    except Exception:
        print(f"ERROR: {url}")
        return None

    # Find all movie items
    return driver.find_elements(By.CLASS_NAME, "griditem")


def scrape_ratings(initials, username, cur):
    '''updates database with user movie ratings'''

    global scraped

    # get ratings data
    for page in range(1, 26):

        # scrape webpage
        url = f'https://letterboxd.com/{username}/films/by/date/page/{page}/'
        movies = scrape(url)

        # get rating for all movies in the page
        print(f'Scraping: {username} page {page} movies {len(movies)}')
        for movie in movies:

            # get movie data
            filmid = int(movie.find_element(By.CLASS_NAME, "react-component").get_attribute("data-film-id"))
            date = movie.find_element(By.TAG_NAME, "time").get_attribute("datetime")[0:10]
            rating = movie.find_element(By.CLASS_NAME, "rating").text.strip()
            rating = rating.count('★') + 0.5 * rating.count('½')
            cur.execute(f'INSERT INTO ratings VALUES {(initials, filmid, date, rating)};')

        # pause every 5th page to prevent website blocking requests
        time.sleep(random.uniform(3, 7))
        # scraped += 1
        # if scraped > 4:
        #     scraped = 0
        #     sleep(90)


        # check if still within eligibility period
        if strptime(date, '%Y-%M-%d') < START_DATE:
            return None
        
        sleep(3) # slow down scraping to avoid being blocked by letterboxd


def scrape_movies(cur, table):
    '''updates database with movies on watchlist'''

    global scraped

    # slow down scraping to avoid being blocked by letterboxd
    if scraped > 4:
        scraped = 0
        sleep(90)

    # scrape full watchlist
    record = 1
    movies = scrape(URLS[table])
    print(f'Scraping: {table} movies {len(movies)}')
    for movie in movies:
        filmid = int(movie.find_element(By.CLASS_NAME, "react-component").get_attribute("data-film-id"))
        react_data = movie.find_element(By.CLASS_NAME, "react-component")
        slug = react_data.get_attribute("data-item-slug")
        title = react_data.get_attribute("data-item-name")
        title = ' '.join([word if '(202' not in word else '' for word in title.split(' ')])[:-1] # remove 2025 from title
        cur.execute(f'INSERT INTO {table} VALUES {(filmid, slug, title, record)};')
        record += 1
    

def main():
    '''
    Web scrapes letterboxd film ratings for specified users
    Creates tables with results

    TABLES
    users: (initials, user)
    ratings: (initials, filmid, date, rating)
    movies: (filmid, title) 
    awards: (filmid, award)
    '''
    # remove old database
    if os.path.exists("letterboxrs.db"):
        os.remove("letterboxrs.db")

    # open new database connection and cursor
    conn = sqlite3.connect('letterboxrs.db')
    cur = conn.cursor()
    initialize_tables(cur)

    # get user data
    for user in USERS:
        cur.execute(f'INSERT INTO users VALUES {user};')
        scrape_ratings(user[0], user[1], cur)
        sleep(3) # slow down scraping to avoid being blocked by letterboxd
        
    # get movie data
    scrape_movies(cur, 'movies')
    if URLS['oscars']:
        scrape_movies(cur, 'oscars')
        sleep(3) # slow down scraping to avoid being blocked by letterboxd

    # commit changes and close database connection
    conn.commit()
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()


driver.quit()