import requests
import sqlite3
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


def scrape_ratings(users):
    '''returns lists of tuples representing:
    (1) movie ratings for each user
    (2) rated movies'''
    ratings = []
    rated_movies = []
    for user in users:
        initial = user[0]
        username = user[1]

        # scrape first page
        url = f'https://letterboxd.com/{username}/films/by/rated-date/size/large'
        soup = scrape(url)

        # determine number of pages to web scrape
        pages = [tag.text for tag in soup.find_all('li', {'class': 'paginate-page'})]
        if not pages:
            pages = [1]
        if '…' in pages:
            pages = list(range(1, int(pages[-1]) + 1))

        # get ratings data
        for page in [1]:#pages:
            # update user and page progress
            print(f'Scraping: {username} page {page}.')

            # scrape next page if after first page
            if page != '1':
                url = f'https://letterboxd.com/{username}/films/by/rated-date/size/large/page/{page}/'
                soup = scrape(url)
            
            # get rating for all movies in page
            movies = soup.find_all('li', {'class': 'poster-container'})
            for movie in movies:
                id = int(movie.div['data-film-id'])
                title = movie.div['data-film-slug'].replace('-', ' ').title() #get div data-key
                movie_data = movie.find('p', {'class': 'poster-viewingdata'})
                date = movie_data.find('time')['datetime'][0:10]
                rating = movie_data.text
                rating = rating.count('★') + 0.5 * rating.count('½')

                # add movie data to lists if rating exists
                if rating > 0:
                    ratings.append((initial, id, date, rating))
                    rated_movies.append((id, title))
    return ratings, list(set(rated_movies))


def scrape_movies(rated_movies):
    '''returns lists of tuples representing:
    (1) movies
    (2) actors
    (3) genres'''

    movies = []
    actors = []
    genres = []
    for movie in rated_movies:
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
        movies.append((id, title, year, director, runtime))

        # get stars ie top 3 cast
        try:
            cast = soup.find('div', {'id': 'tab-cast'}).find_all('a')
            cast = [member.text for member in cast[:3]]
            for actor in cast:
                actors.append((id, actor))
        except:
            print(f'*** Error: no cast for {title} ***')

        # get genres
        try:
            movie_genres = soup.find('div', {'id': 'tab-genres'}).find('div', {'class': 'text-sluglist capitalize'}).find_all('a')
            movie_genres = [genre.text for genre in movie_genres]
            for genre in movie_genres:
                genres.append((id, genre))
        except:
            print(f'*** Error: no genres for {title} ***')

    return movies, actors, genres


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
    ratings, rated_movies = scrape_ratings([users[2]])
    movies, actors, genres = scrape_movies(rated_movies)

    # write results to db
    for name, data in zip(('users', 'ratings', 'movies', 'actors', 'genres'), (users, ratings, movies, actors, genres)):
        cur.execute(f'''INSERT INTO {name} VALUES {','.join([f"{x}" for x in data])}''')

    # commit changes and close database connection
    conn.commit()
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()