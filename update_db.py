import os
import requests
import sqlite3
from bs4 import BeautifulSoup
from time import sleep, strptime

# constants
START_DATE = strptime('2024-12-01','%Y-%m-%d')
URLS = {'movies': 'https://letterboxd.com/_branzino/list/oscars-2026/',
        'oscars':''}
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
    '''returns web scraping aka beautifulsoup "soup" '''
    html = requests.get(url)
    return BeautifulSoup(html.content, 'html.parser')


def scrape_ratings(initials, username, cur):
    '''updates database with user movie ratings'''

    # get ratings data
    for page in range(1, 26):

        # scrape webpage
        url = f'https://letterboxd.com/{username}/films/by/date/size/large/page/{page}/'
        soup = scrape(url)

        # get rating for all movies in the page
        movies = soup.find_all('li', {'class': 'griditem'})
        print(f'Scraping: {username} page {page} movies {len(movies)}')
        for movie in movies:

            # get movie data
            filmid = int(movie.div['data-film-id'])
            movie_data = movie.find('p', {'class': 'poster-viewingdata'})
            date = movie_data.find('time')['datetime'][0:10]
            rating = movie_data.text
            rating = rating.count('★') + 0.5 * rating.count('½')
            cur.execute(f'INSERT INTO ratings VALUES {(initials, filmid, date, rating)};')
        
        # check if still within eligibility period
        if strptime(date, '%Y-%M-%d') < START_DATE:
            return None
        
        # pause every 5th page to prevent website blocking requests
        if page % 5 == 0:
            sleep(90) 
        
        sleep(3) # slow down scraping to avoid being blocked by letterboxd


def scrape_movies(cur, db):
    '''updates database with movies on watchlist'''

    # scrape full watchlist
    record = 1
    soup = scrape(URLS[db])
    movies = soup.find_all('li', {'class': 'posteritem'})
    for movie in movies:
        filmid = int(movie.div['data-film-id'])
        slug = movie.div['data-item-slug']
        title = movie.div['data-item-name']
        title = ' '.join([word if '(202' not in word else '' for word in title.split(' ')])[:-1] # remove 2025 from title
        cur.execute(f'INSERT INTO {db} VALUES {(filmid, slug, title, record)};')
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
        sleep(90) # pause to prevent website blocking requests
    
    # get movie data
    scrape_movies(cur, 'movies')
    if URLS['oscars']:
        scrape_movies(cur, 'oscars')

    # commit changes and close database connection
    conn.commit()
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()