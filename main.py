import requests
import sqlite3
import pandas as pd
from bs4 import BeautifulSoup


def initialize_tables(cur):
    '''create database tables if not already existing'''

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
                    initials    char(2) PRIMARY KEY,
                    "user"      varchar(20), 
                    "name"      varchar(20)
                );''')

    cur.execute('''CREATE TABLE IF NOT EXISTS ratings (
                    initials    char(2),
                    id          integer, 
                    "date"      date,
                    rating      decimal,
                    PRIMARY KEY (id, initials)
                );''')

    cur.execute('''CREATE TABLE IF NOT EXISTS movies (
                    id          integer PRIMARY KEY,
                    title       varchar(100), 
                    year        smallint,
                    director    varchar(40),
                    runtime     smallint
                );''')

    cur.execute('''CREATE TABLE IF NOT EXISTS actors (
                    id          integer,
                    actor       varchar(40),
                    PRIMARY KEY (id, actor)
                );''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS genres (
                    id          integer,
                    genre       varchar(40),
                    PRIMARY KEY (id, genre)
                );''')
    

def scrape(url):
    '''returns web scraping aka beautifulsoup "soup" '''
    html = requests.get(url)
    return BeautifulSoup(html.content, 'html.parser')


def scrape_ratings(users, cur):
    '''updates database with new movie ratings by users
    returns list of newly added movies (id, title)'''
    
    existing_ratings = cur.execute('SELECT initials,id FROM ratings').fetchall()

    added_movies = []
    for user in users:
        initials = user[0]
        username = user[1]

        # get id of most recent rating in db
        last_rated = cur.execute('SELECT id FROM ratings ORDER BY date DESC LIMIT 1;').fetchone()
        if not last_rated:
            last_rated = -1
        else:
            last_rated = last_rated[0]

        # scrape first page
        url = f'https://letterboxd.com/{username}/films/by/rated-date/size/large'
        soup = scrape(url)

        # determine final page to web scrape
        last_page = soup.find_all('li', {'class': 'paginate-page'}) or 1
        if last_page != 1: last_page = int(last_page[-1].text)

        # get ratings data
        page = 1
        keep_going = True
        while page <= last_page and keep_going:
            # update user and page progress
            print(f'Scraping: {username} page {page}.')

            # scrape next page if after first page
            if page != '1':
                url = f'https://letterboxd.com/{username}/films/by/rated-date/size/large/page/{page}/'
                soup = scrape(url)

            # get rating for all movies in page
            movies = soup.find_all('li', {'class': 'poster-container'})
            for movie in movies:
                # get movie id and check if user already rated (delete if so)
                id = int(movie.div['data-film-id'])
                if (initials, id) in existing_ratings:
                    cur.execute(f'DELETE FROM ratings WHERE initials="{initials}" and id={id};')
                
                # get movie data
                title = movie.div['data-film-slug'].replace('-', ' ').title() #get div data-key
                movie_data = movie.find('p', {'class': 'poster-viewingdata'})
                date = movie_data.find('time')['datetime'][0:10]
                rating = movie_data.text
                rating = rating.count('★') + 0.5 * rating.count('½')

                # add rating data to db if rating exists
                if rating > 0:
                    cur.execute(f'INSERT INTO ratings VALUES {(initials, id, date, rating)};')
                    added_movies.append((id, title))
                
                # stop adding more movies if id was the last one present in database
                if id == last_rated:
                    print('last rated movie encountered')
                    keep_going = False
                    break
            page += 1

    return list(set(added_movies))


def scrape_movies(added_movies, cur):
    '''webscrapes movie, actor, and genre data for added_movies
    adds data to tables in db if not already present'''

    existing_movies = cur.execute('SELECT id,title FROM movies').fetchall()

    for movie in added_movies:
        # skip movie if it already exists db
        if movie in existing_movies:
            continue

        id = movie[0]
        title = movie[1]

        # update progress
        print(f'Scraping: {title}')

        # scrape film webpage
        url = f"https://letterboxd.com/film/{title.replace(' ', '-').lower()}/"
        soup = scrape(url)

        # get year and director
        header_data = soup.find('section', {'id': 'featured-film-header'}).find_all('a')
        year = header_data[0].text
        director = header_data[1].text

        # get run time
        runtime = soup.find('p', {'class': 'text-link text-footer'}).text
        runtime = int(runtime.replace('\t', '').replace('\n', '').split('\xa0')[0] )

        # add film data to movies list
        cur.execute(f'INSERT INTO movies VALUES {(id, title, year, director, runtime)};')

        # get stars ie top 3 cast
        try:
            cast = soup.find('div', {'id': 'tab-cast'}).find_all('a')
            cast = [member.text for member in cast[:3]]
            for actor in cast:
                cur.execute(f'INSERT INTO actors VALUES {(id, actor)};')
        except:
            print(f'*** Error: no cast for {title} ***')

        # get genres
        try:
            movie_genres = soup.find('div', {'id': 'tab-genres'}).find('div', {'class': 'text-sluglist capitalize'}).find_all('a')
            movie_genres = [genre.text for genre in movie_genres]
            for genre in movie_genres:
                cur.execute(f'INSERT INTO genres VALUES {(id, genre)};')
        except:
            print(f'*** Error: no genres for {title} ***')


def main():
    '''
    Web scrapes letterboxd film ratings for specified users
    Creates tables with results

    TABLES
    users: (user, name, initial)
    ratings: (initial, filmid, rating)
    movies: (filmid, title, year, director, runtime)    
    actors: (filmid, actor)
    genres: (filmid, genre)
    '''
    # open database connection and cursor
    conn = sqlite3.connect('movie_data.db')
    cur = conn.cursor()

    # initialize tables
    initialize_tables(cur)

    # specify users to include
    users = [('BC', 'bcunnane', 'Brandon'),
             ('MF', 'mfrye', 'Missy'),
             ('DN', 'nbditsd', 'Darien'),
             ('NB', 'NikkiBerry', 'Nikki'),
             ('CA', 'latenight_', 'Corey'),
             ('TA', 'tarias', 'Tommie')]
    
    # web scrape data for tables
    added_movies = scrape_ratings([users[1]], cur)
    scrape_movies(added_movies, cur)

    qry = 'SELECT * FROM ratings;'
    ratings = pd.read_sql(qry, conn)

    # commit changes and close database connection
    conn.commit()
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()