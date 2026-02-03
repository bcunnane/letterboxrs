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



def setup_driver():
    # Setup Chrome WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # Add a User-Agent to mimic a real browser
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def scrape_ratings(initials, url):
    '''updates database with user movie ratings'''
    #initialize
    ratings = pd.DataFrame(columns=['initials','filmid','rating'])
    movies = pd.DataFrame(columns=['filmid','title', 'slug'])

    # scrape
    driver = setup_driver()
    driver.get(url)

    try:
        # Wait for the page content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "film-poster"))
        )
    except Exception:
        print(f"ERROR: {url}")
        return None

    posters = driver.find_elements(By.CLASS_NAME, "griditem")

    # get rating for all posters in the page
    for poster in posters:

        # get movie data
        filmid = int(poster.find_element(By.CLASS_NAME, "react-component").get_attribute("data-film-id"))
        react_data = poster.find_element(By.CLASS_NAME, "react-component")
        slug = react_data.get_attribute("data-item-slug")
        title = react_data.get_attribute("data-item-name")
        # date = movie.find_element(By.TAG_NAME, "time").get_attribute("datetime")[0:10]
        try:
            rating = poster.find_element(By.CLASS_NAME, "rating").text.strip()
            rating = rating.count('★') + 0.5 * rating.count('½')
        except:
            rating = 0

        ratings.loc[len(ratings)] = {'initials':initials, 'filmid':filmid, 'rating':rating}
        movies.loc[len(movies)] = {'filmid':filmid, 'title':title, 'slug':slug}
        
    return ratings, movies


def scrape_movielist(year, url):
    '''updates database with movies on watchlist'''
    #initialize
    movielist = pd.DataFrame(columns=['year','filmid'])
    movies = pd.DataFrame(columns=['filmid','title', 'slug'])

    # scrape
    driver = setup_driver()
    driver.get(url)

    try:
        # Wait for the page content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.poster-list"))
        )
    except Exception:
        print(f"ERROR: {url}")
        # return None

    posters = driver.find_elements(By.CLASS_NAME, "posteritem")

    # get rating for all posters in the page
    for poster in posters:

        # get movie data
        react_data = poster.find_element(By.CLASS_NAME, "react-component")
        filmid = int(react_data.get_attribute("data-film-id"))
        slug = react_data.get_attribute("data-item-slug")
        title = react_data.get_attribute("data-item-name")

        movielist.loc[len(movielist)] = {'year':year, 'filmid':filmid}
        movies.loc[len(movies)] = {'filmid':filmid, 'title':title, 'slug':slug}
        
    # quit driver to avoid bot detector
    driver.quit()

    return movielist, movies
    

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


    # all_ratings = pd.read_csv('data\\ratings.csv')
    # all_movies = pd.read_csv('data\\movies.csv')
    
    # page = 1
    # user = USERS[0]
    # url = f'https://letterboxd.com/{user[1]}/films/by/date/page/{page}/'
    
    # # all_ratings, all_movies = scrape_ratings(user[0], url)

    # new_ratings, new_movies = scrape_ratings(user[0], url)
    # all_ratings = pd.concat([new_ratings, all_ratings]).drop_duplicates()
    # all_movies = pd.concat([new_movies, all_movies]).drop_duplicates()

    # all_ratings.to_csv('data\\ratings.csv', index=False)
    # all_movies.to_csv('data\\movies.csv', index=False)

    URLS = {'movies': 'https://letterboxd.com/_branzino/list/oscars-2026/',
            'oscars':'https://letterboxd.com/000_leo/list/oscars-2026-1/'}

    noms, movies = scrape_movielist('2025', 'https://letterboxd.com/000_leo/list/oscars-2026-1/')


    noms.to_csv('data\\noms.csv', index=False)


    # get movie data
    # scrape_movies(cur, 'movies')
    # if URLS['oscars']:
    #     scrape_movies(cur, 'oscars')
    #     sleep(3) # slow down scraping to avoid being blocked by letterboxd



if __name__ == '__main__':
    main()

