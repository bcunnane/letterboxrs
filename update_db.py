import os
import requests
import sqlite3
from bs4 import BeautifulSoup

# constants
WATCH_LIST_URL = 'https://letterboxd.com/_branzino/list/movie-szn-2025/'
BEST_PIC_URL = 'https://letterboxd.com/mostlyjo/list/best-picture-2024/'
START_DATE = '01-01-2024'
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
    
    cur.execute('''CREATE TABLE IF NOT EXISTS bestpic (
                    filmid      integer PRIMARY KEY
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

            # add rating data to db if rating exists
            if rating > 0:
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
    
    # scrape best picture list
    # soup = scrape(BEST_PIC_URL)
    # movies = soup.find_all('li', {'class': 'poster-container'})
    # for movie in movies:
    #     filmid = int(movie.div['data-film-id'])
    #     cur.execute(f'INSERT INTO bestpic (filmid) VALUES ({filmid});')


def main():
    '''
    Web scrapes letterboxd film ratings for specified users
    Creates tables with results

    TABLES
    users: (initials, user)
    ratings: (initials, filmid, date, rating)
    movies: (filmid, title) 
    '''
    # remove old database
    if os.path.exists("letterboxrs.db"):
        os.remove("letterboxrs.db")

    # open new database connection and cursor
    conn = sqlite3.connect('letterboxrs.db')
    cur = conn.cursor()

    # fill tables
    initialize_tables(cur)
    scrape_movies(cur)
    for user in USERS:
        cur.execute(f'INSERT INTO users VALUES {user};')
        scrape_ratings(user[0], user[1], cur)

    # commit changes and close database connection
    conn.commit()
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()