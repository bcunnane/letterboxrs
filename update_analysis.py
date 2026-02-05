import datetime
import pandas as pd


def filmids_to_posters(df):
    """convert film ids to movie posters
    expects dataframe with columns filmid and slug"""
    
    df['filmid'] = df['filmid'].astype(str)

    # convert filmid to poster image
    posters = []
    for index,row in df.iterrows():
        slug = row['slug']
        posters.append(f'''<img src="https://a.ltrbxd.com/resized/film-poster/{'/'.join(row['filmid'])}/{row['filmid']}-{slug}-0-1000-0-1500-crop.jpg" alt="{row['slug']}" style="height: 105px; width:70px;"/>''')
    
    df['filmid'] = posters
    df.rename(columns={"filmid": "Movie"}, inplace=True)
    return df


def main():

    # import movie data
    movies = pd.read_csv('data\\movies.csv')
    ratings = pd.read_csv('data\\ratings.csv')
    ratings = movies.merge(ratings, how='inner', on='filmid')

    # import year-specific data
    year = 2026
    noms = pd.read_csv('data\\noms.csv')
    noms = noms[noms['list'] == year][['filmid', 'best_pic']]
    watchlist = pd.read_csv('data\\watchlist.csv')
    watchlist = watchlist[watchlist['list'] == year]

    # apply year data to movie data
    ratings = ratings.merge(watchlist, how='inner', on='filmid')
    ratings = ratings.merge(noms, how='left', on='filmid')

    # get leaderboard data
    total = ratings.groupby('user')['user'].count()
    best_pic = ratings[ratings['best_pic']==1].groupby('user')['user'].count()
    oscar_pct = 100 * ratings[ratings['best_pic'].notna()].groupby('user')['user'].count() / len(noms)

    # rename leaderboard columns
    total.rename('Total', inplace=True)
    best_pic.rename('Best Pics', inplace=True)
    oscar_pct.rename('Oscar %', inplace=True)

    # compile leaderboard
    leader = pd.concat([
        total
        , best_pic
        , oscar_pct.astype(int)
    ], axis=1)
    leader = leader.sort_values(by='Total', ascending=False)
    leader.rename_axis("Name", axis=0, inplace=True)
    leader = leader.to_markdown()

    # compile aggregate movie data
    non_zero_ratings = ratings[ratings['rating']>0]
    agg_movie_data = non_zero_ratings.groupby(['filmid', 'slug'])['rating'].agg(
        Std='std',
        Min='min',
        Ave='mean',
        Max='max',
        Views='count'
    ).reset_index()
    agg_movie_data = agg_movie_data[agg_movie_data['Views'] > 2] # must have 3 ratings
    agg_movie_data = filmids_to_posters(agg_movie_data)

    # get best movies
    best_movies = agg_movie_data[agg_movie_data['Ave'] >= 3.0]
    best_movies = best_movies[['Movie', 'Ave', 'Views']].sort_values(by='Ave', ascending=False)[:7]
    best_movies = best_movies.to_markdown(index=False, floatfmt=".2f")

    # get worst movies
    worst_movies = agg_movie_data[agg_movie_data['Ave'] < 3.0]
    worst_movies = worst_movies[['Movie', 'Ave', 'Views']].sort_values(by='Ave', ascending=True)[:5]
    worst_movies = worst_movies.to_markdown(index=False, floatfmt=".2f")

    # get controversial movies
    controversial = agg_movie_data.sort_values(by='Std', ascending=False)[:5]
    controversial = controversial[['Movie','Min', 'Ave', 'Max','Views']].to_markdown(index=False, floatfmt=".1f")

    # compile harshest critics data
    critics = non_zero_ratings.groupby('user')['rating'].agg(
        Ave='mean',
        Min='min',
    ).reset_index().sort_values(by=['Ave', 'Min'])
    critics.rename(columns={'user': 'Name'}, inplace=True)
    critics = critics.to_markdown(index=False, floatfmt=".2f")

    # get watched
    watched = ratings[['user', 'slug', 'rating']].copy()
    watched.rename(columns={'user': 'Name', 'slug':'Movie', 'rating':'Rating'}, inplace=True)
    watched['Rating'] = watched['Rating'].astype(str)

    # remove 0 ratings aka "watched" moves
    watched.loc[watched['Rating'] == '0.0', 'Rating'] = 'X'

    # create pivot table
    watched = watched.pivot(index='Movie', columns='Name', values='Rating')
    watched[watched.isnull()] = ''
    
    # split table into groups of n movies
    n = 8
    watched = [watched.iloc[i:i+n].to_markdown(floatfmt=".1f") for i in range(0, watched.shape[0], n)]

    # update README.md
    output = f'''Aggregate Letterboxd movie ratings for 2026! <br />
Last updated on {datetime.datetime.now().strftime('%a %b %d at %I:%M %p')} <br />
Watchlist can be found [here](https://letterboxd.com/_branzino/list/oscars-2026/)

## Leaderboard :trophy:
{leader}

## Loved Movies :heart:
{best_movies}

## Unloved Movies :broken_heart:
{worst_movies}

## Controversial Movies :hot_pepper:
{controversial}

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