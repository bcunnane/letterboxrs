import sqlite3
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def ave_ratings(conn):

    # pull average rating data from db
    qry =   '''SELECT m.title, ROUND(AVG(r.rating),1) AS ave_rating
            FROM ratings r
            JOIN movies m ON m.id = r.id
            GROUP BY title
            HAVING count(*) > 2 AND m.runtime > 59'''
    ave_ratings = pd.read_sql(qry, conn)

    # sort to reveal best and worst movies
    bad_movies = ave_ratings.sort_values(by=['ave_rating'])[:10]
    good_movies = ave_ratings.sort_values(by=['ave_rating'], ascending=False)[:10]

    # convert dfs to markdown
    bad_movies = bad_movies.to_markdown(index=False, floatfmt=".1f")
    good_movies = good_movies.to_markdown(index=False, floatfmt=".1f")

    return bad_movies, good_movies


def harshest_critic(conn):
    qry =   '''SELECT r.initials, ROUND(AVG(rating), 1) AS ave_rating
            FROM ratings r
            JOIN movies m ON r.id=m.id
            GROUP BY r.initials
            HAVING m.runtime > 59
            ORDER BY ave_rating;'''
    harsh_critic = pd.read_sql(qry, conn)
    return harsh_critic.to_markdown(index=False, floatfmt=".1f")


def velocity(conn):
    start_date = '2024-04-01'
    qry =   f'''SELECT r.initials, strftime('%W', r.date) AS week, count(*) AS "count"
            FROM ratings r
            JOIN movies m on r.id=m.id
            GORUP BY r.initials, week
            HAVING r.date > '{start_date}' and m.runtime > 59
            ORDER BY r.initials;'''
    velocity = pd.read_sql(qry, conn)


def controversial(ratings):

    # get standard deviations and counts for rated movies
    stds = ratings.groupby('title').rating.std()
    counts = ratings.groupby('title').rating.count()

    # combine data into df and filter
    contros = pd.DataFrame([stds,counts], index=['stds','counts']).transpose()
    contros = contros[(contros.stds > 1.5) & (contros.counts > 2)]
    contros.sort_values(by=['stds'], ascending=False, inplace=True)

    # show votes for controversial movies
    contro_ratings = ''
    for title in contros.index:
        votes = ratings[ratings['title'] == title].sort_values(by=['rating'], ascending=False)
        contro_ratings += f'''{title}
{votes[['initials', 'rating']].to_markdown(index=False, floatfmt=".1f")}

'''
    return contro_ratings[:-2]


def watched(ratings, noms):

    # initialized df: index=nominated_films, columns=initials
    watched = pd.DataFrame(index=noms.title, columns=ratings.initials.unique())
    watched[:] = ''

    # filter ratings df to only include nominated movies
    ratings = ratings[ratings.title.isin(watched.index)]

    # loop through users and set what they've seen
    for initial in watched.columns:
        watched.loc[ratings[ratings.initials == initial].title, initial] = 'X'
    
    return watched.to_markdown(), (watched == 'X').sum().to_markdown()


def main():

    # open database connection and cursor
    conn = sqlite3.connect('movie_data.db')
    cur = conn.cursor()

    # pull all movie ratings data
    qry =   '''SELECT r.initials, m.title, r.rating
            FROM ratings r JOIN movies m ON r.id=m.id
            WHERE m.runtime > 59;'''
    ratings = pd.read_sql(qry, conn)

    # pull all nominations
    qry =   '''SELECT m.title
            FROM noms n JOIN movies m
            ON n.id = m.id
            WHERE n.year = 2024;'''
    noms = pd.read_sql(qry, conn)
    
    # perform analysis
    bad_movies, good_movies = ave_ratings(conn)
    contro_ratings = controversial(ratings)
    critics = harshest_critic(conn)
    seen, count = watched(ratings, noms)


    # close database connection
    cur.close()
    conn.close()

    # update README.md
    output = f'''[Home](https://bcunnane.github.io/) | [Repository](https://github.com/bcunnane/movie_tracker)

### Favorite Movies
{good_movies}

### Hated Movies
{bad_movies}

### Controversial Movies
{contro_ratings}

### Harshest Critic
{critics}

### Watched
{seen}

### Watched Count
{count}'''
    
    f = open('README.md', 'w')
    f.write(output)
    f.close()


if __name__ == '__main__':
    main()