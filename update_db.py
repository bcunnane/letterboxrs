import os
import requests
import sqlite3
from bs4 import BeautifulSoup

# constants
WATCH_LIST_URL = 'https://letterboxd.com/_branzino/list/movie-szn-2025/'
START_DATE = '01-01-2024'
AWARD_URL = {'oscars':'https://letterboxd.com/000_leo/list/oscars-2025-1/',
             'indies':'https://letterboxd.com/outtothemovies/list/indie-spirit-awards-2025/'}
AWARD_NUM = {'oscars':10, 'indies':5}
USERS = [('BC', '_branzino'),
         ('CA', 'honeydijon2'),
         ('DN', 'nbditsd'),
         ('KH', 'shewasak8rgrl'),
         ('MF', 'mfrye'),
         ('MT', 'michelletreiber'),
         ('NB', 'NikkiBerry'),
         ('RZ', 'BOBBY_ZEE'),
         ('TA', 'tarias')]


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
                    title       varchar(40)
                );''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS awards (
                    filmid      integer,
                    award       varchar(20),
                    PRIMARY KEY (filmid, award)
                );''')


def scrape(url):
    '''returns web scraping aka beautifulsoup "soup" '''
    html = requests.get(url)
    return BeautifulSoup(html.content, 'html.parser')


def scrape_ratings(initials, username, cur):
    '''updates database with user movie ratings'''

    # scrape first page
    url = f'https://letterboxd.com/{username}/films/by/rated-date/size/large'
    soup = scrape(url)

    # determine final page to web scrape
    last_page = soup.find_all('li', {'class': 'paginate-page'}) or 1
    if last_page != 1: last_page = int(last_page[-1].text)

    # get ratings data
    page = 1
    while page <= last_page:
        # update user and page progress
        print(f'Scraping: {username} page {page}')

        # get rating for all movies in each page
        movies = soup.find_all('li', {'class': 'poster-container'})
        for movie in movies:

            # get movie data
            filmid = int(movie.div['data-film-id'])
            movie_data = movie.find('p', {'class': 'poster-viewingdata'})
            date = movie_data.find('time')['datetime'][0:10]
            rating = movie_data.text
            rating = rating.count('★') + 0.5 * rating.count('½')
            cur.execute(f'INSERT INTO ratings VALUES {(initials, filmid, date, rating)};')
            
            # check if still within eligibility period
            if date < START_DATE:
                 return None
        
        # increment page and scrape
        page += 1
        url = f'https://letterboxd.com/{username}/films/by/rated-date/size/large/page/{page}/'
        soup = scrape(url)


def scrape_movies(cur):
    '''updates database with movies on watchlist'''

    # scrape full watchlist
    soup = scrape(WATCH_LIST_URL)
    movies = soup.find_all('li', {'class': 'poster-container'})
    for movie in movies:
        filmid = int(movie.div['data-film-id'])
        slug = movie.div['data-film-slug']
        title = movie.find('img')['alt']
        cur.execute(f'INSERT INTO movies VALUES {(filmid, slug, title)};')
    
def scrape_awards(cur, award):
    '''updates database with oscars and indie spirit awards best pictures'''

    if AWARD_URL[award]:
        soup = scrape(AWARD_URL[award])
        movies = soup.find_all('li', {'class': 'poster-container'})
        for i in range(AWARD_NUM[award]):
            movie = movies[i]
            filmid = int(movie.div['data-film-id'])
            cur.execute(f'INSERT INTO awards VALUES {(filmid, award)};')
    

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
    
    # get movie data
    scrape_movies(cur)
    for award in ['oscars', 'indies']:
        scrape_awards(cur, award)

    # commit changes and close database connection
    conn.commit()
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()