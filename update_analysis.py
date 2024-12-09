import sqlite3
import datetime
import pandas as pd

def get_leader(conn):
    '''Collect users with most watched movies'''

    qry = '''SELECT
                r.initials AS 'Name'
                , COUNT(*) AS 'Total'
                --, COUNT(O.filmid) AS 'Oscars'
                , COUNT(g.filmid) AS 'Globes'
                , COUNT(i.filmid) AS 'Indies'
            FROM movies m
            INNER JOIN ratings r
                ON m.filmid = r.filmid
            LEFT OUTER join awards o
                on m.filmid = o.filmid
                and o.award = 'oscars'
            LEFT OUTER join awards g
                on m.filmid = g.filmid
                and g.award = 'globes'
            LEFT OUTER join awards i
                on m.filmid = i.filmid
                and i.award = 'indies' 
            GROUP BY r.initials
            ORDER BY Total DESC
                --, Oscars DESC
                , Globes DESC
                , Indies DESC;'''
    leader = pd.read_sql(qry, conn)
    return leader.to_markdown(index=False)


def filmids_to_posters(df):
    """convert film ids to movie posters
    expects dataframe with columns filmid and slug"""
    
    df['filmid'] = df['filmid'].astype(str)

    # film years to delete from slug
    YEARS = ['20' + str(x) for x in range(20, 30)]

    # convert filmid to poster image
    posters = []
    for index,row in df.iterrows():
        
        # remove YEAR from slug if present
        slug = row['slug']
        if slug.split('-')[-1] in YEARS:
            slug = '-'.join(slug.split('-')[:-1])
        
        # get movie poster links 
        posters.append(f'''<img src="https://a.ltrbxd.com/resized/film-poster/{'/'.join(row['filmid'])}/{row['filmid']}-{slug}-0-1000-0-1500-crop.jpg" alt="{row['slug']}" style="height: 105px; width:70px;"/>''')
    
    df['filmid'] = posters
    df.rename(columns={"filmid": "Movie"}, inplace=True)
    return df


def get_ave_ratings(conn, t, limit=5):
    '''Collect best and worst average movie ratings
    t: scoring type. either "best" or "worst" ratings'''
    CUT_PT = 3

    ineq = {'best':'>=', 'worst':'<'}
    ordering = {'best':'DESC', 'worst':'ASC'}

    qry = f'''SELECT
                r.filmid
                , m.slug
                , ROUND(AVG(r.rating),2) AS 'Ave Rating'
                , COUNT(*) AS 'Views'
            FROM movies m
            JOIN ratings r
                ON m.filmid = r.filmid
            WHERE r.rating > 0
            GROUP BY r.filmid
            HAVING COUNT(*) > 2
                AND AVG(r.rating) {ineq[t]} {CUT_PT}
            ORDER BY AVG(r.rating) {ordering[t]}, Views DESC'''
    ave_ratings = pd.read_sql(qry, conn)

    # convert filmids to movie posters
    ave_ratings = filmids_to_posters(ave_ratings)
    
    # Remove slug from dataframe
    del ave_ratings['slug']

    return ave_ratings[:limit].to_markdown(index=False, floatfmt=".2f")


def get_harshest_critic(conn):
    '''Collect users with lowest average ratings'''

    qry = '''SELECT
                r.initials AS 'Name'
                , ROUND(AVG(r.rating), 1) AS 'Ave'
                , MIN(r.rating) AS 'Lowest'
            FROM ratings r
            JOIN movies m
                ON r.filmid = m.filmid
            WHERE r.rating > 0
            GROUP BY r.initials
            ORDER BY AVG(rating);'''
    critics = pd.read_sql(qry, conn)
    return critics.to_markdown(index=False, floatfmt=".1f")


def get_watched(conn):
    '''Collect all user ratings'''

    qry = '''SELECT
                r.initials AS 'Name'
                , m.title AS 'Movie'
                , r.rating AS 'Rating'
            FROM movies m
            JOIN ratings r  
                ON m.filmid = r.filmid;'''
    watched = pd.read_sql(qry, conn)

    # convert numerical columns to strings
    watched['Movie'] = watched['Movie'].astype(str)
    watched['Rating'] = watched['Rating'].astype(str)

    # remove 0 ratings aka "watched" moves
    watched.loc[watched['Rating'] == '0.0', 'Rating'] = 'X'

    # create pivot table
    watched = watched.pivot(index='Movie', columns='Name', values='Rating')
    watched[watched.isnull()] = ''
    
    # split table into groups of n movies
    n = 8
    return [watched.iloc[i:i+n].to_markdown(floatfmt=".1f") for i in range(0, watched.shape[0], n)]


def main():

    # open database connection and cursor
    conn = sqlite3.connect('letterboxrs.db')
    cur = conn.cursor()
    
    # collect tables
    leader = get_leader(conn)
    best_movies = get_ave_ratings(conn, 'best', limit=7)
    worst_movies  = get_ave_ratings(conn, 'worst', limit=5)
    critics = get_harshest_critic(conn)
    watched = get_watched(conn)

    # close database connection
    cur.close()
    conn.close()

    # update README.md
    output = f'''Aggregate Letterboxd movie ratings for 2025! <br />
Last updated on {datetime.datetime.now().strftime('%a %b %d at %I:%M %p')} <br />
Watchlist can be found [here](https://letterboxd.com/_branzino/list/movie-szn-2025/)

## Leaderboard :trophy:
{leader}

## Loved Movies :heart:
{best_movies}

## Unloved Movies :broken_heart:
{worst_movies}

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