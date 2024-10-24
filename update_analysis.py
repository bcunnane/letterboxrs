import sqlite3
import pandas as pd

def get_leader(conn):
    '''Collect users with most watched movies'''

    qry = '''SELECT
                r.initials AS 'Name'
                , COUNT(*) AS 'Total'
            FROM movies m
            JOIN ratings r
                ON m.filmid = r.filmid
            GROUP BY r.initials
            ORDER BY COUNT(*) DESC;'''
    leader = pd.read_sql(qry, conn)
    return leader.to_markdown(index=False)


def get_ave_ratings(conn):
    '''Collect best and worst average movie ratings'''

    # film year to delete from slug
    YEARS= ('2023', '2024')

    qry = '''SELECT
                r.filmid AS Movie
                , m.slug
                , ROUND(AVG(r.rating),2) AS 'Ave Rating'
            FROM movies m
            JOIN ratings r
                ON m.filmid = r.filmid
            GROUP BY r.filmid
            HAVING COUNT(*) > 2;'''
    ave_ratings = pd.read_sql(qry, conn)


    # convert filmid to poster image
    ave_ratings['Movie'] = ave_ratings['Movie'].astype(str)
    posters = []
    for index,row in ave_ratings.iterrows():
        
        # remove YEAR from slug if present
        slug = row['slug']
        if slug.split('-')[-1] in YEARS:
            slug = '-'.join(slug.split('-')[:-1])
        
        # get movie poster links 
        posters.append(f'''<img src="https://a.ltrbxd.com/resized/film-poster/{'/'.join(row['Movie'])}/{row['Movie']}-{slug}-0-1000-0-1500-crop.jpg" alt="{row['slug']}" style="height: 105px; width:70px;"/>''')
    ave_ratings['Movie'] = posters
    
    # Remove slug from dataframe
    del ave_ratings['slug']

    # sort to reveal best and worst movies
    cut_pt = 3
    bad_movies = ave_ratings[ave_ratings['Ave Rating'] < cut_pt].sort_values(by=['Ave Rating'])[:5]
    good_movies = ave_ratings[ave_ratings['Ave Rating'] >= cut_pt].sort_values(by=['Ave Rating'], ascending=False)[:5]

    # convert dfs to markdown
    bad_movies = bad_movies.to_markdown(index=False, floatfmt=".2f")
    good_movies = good_movies.to_markdown(index=False, floatfmt=".2f")

    return bad_movies, good_movies


def get_harshest_critic(conn):
    '''Collect users with lowest average ratings'''

    qry = '''SELECT
                r.initials AS 'User'
                , ROUND(AVG(r.rating), 1) AS 'Ave'
                , MIN(r.rating) AS 'Lowest'
            FROM ratings r
            JOIN movies m
                ON r.filmid = m.filmid
            GROUP BY r.initials
            ORDER BY AVG(rating);'''
    critics = pd.read_sql(qry, conn)
    return critics.to_markdown(index=False, floatfmt=".1f")


def get_watched(conn):
    '''Collect all user ratings'''

    qry = '''SELECT
                r.initials AS 'User'
                , m.title AS 'Movie'
                , r.rating AS 'Rating'
            FROM movies m
            JOIN ratings r  
                ON m.filmid = r.filmid;'''
    watched = pd.read_sql(qry, conn)

    # convert numerical columns to strings
    watched['Movie'] = watched['Movie'].astype(str)
    watched['Rating'] = watched['Rating'].astype(str)

    # create pivot table
    watched = watched.pivot(index='Movie', columns='User', values='Rating')
    watched[watched.isnull()] = ''
    
    # split table into groups of n movies
    n = 8
    return [watched.iloc[i:i+n].to_markdown() for i in range(0, watched.shape[0], n)]


def main():

    # open database connection and cursor
    conn = sqlite3.connect('letterboxrs.db')
    cur = conn.cursor()
    
    # collect tables
    leader = get_leader(conn)
    bad_movies, good_movies = get_ave_ratings(conn)
    critics = get_harshest_critic(conn)
    watched = get_watched(conn)

    # close database connection
    cur.close()
    conn.close()

    # update README.md
    output = f'''Aggregate Letterboxd movie ratings for 2025! Watchlist can be found [here](https://letterboxd.com/_branzino/list/movie-szn-2025/)

## Leaderboard :trophy:
{leader}

## Loved Movies :heart:
{good_movies}

## Unloved Movies :broken_heart:
{bad_movies}

## Harshest Critic :thumbsdown:
{critics}

## All Watched :movie_camera:
<div  style="overflow-x: scroll;">

{'\n\n</div>\n\n<div  style="overflow-x: scroll;">\n\n'.join(watched)}

</div>'''
    
    f = open('README.md', 'w', encoding='utf-8')
    f.write(output)
    f.close()


if __name__ == '__main__':
    main()