import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep


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


def scrape(type, label, url):
    '''webscrape letterboxd film data'''
    #initialize
    movielist = pd.DataFrame(columns=[type,'filmid','rating'])
    movies = pd.DataFrame(columns=['filmid','slug'])

    # poster scraping per type
    scraping = {'user':"griditem", 'list':"posteritem"}

    # scrape posters
    driver = setup_driver()
    driver.get(url)

    try:
        # Wait for the page content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "film-poster"))
        )
    except Exception:
        print(f"ERROR: class film-poster not present at {url}")
        return None

    posters = driver.find_elements(By.CLASS_NAME, scraping[type])

    # get rating for all posters in the page
    for poster in posters:

        # get movie data
        react_data = poster.find_element(By.CLASS_NAME, "react-component")
        filmid = int(react_data.get_attribute("data-film-id"))
        slug = react_data.get_attribute("data-item-slug")
        # title = react_data.get_attribute("data-item-name")
        # date = movie.find_element(By.TAG_NAME, "time").get_attribute("datetime")[0:10]
        try:
            rating = poster.find_element(By.CLASS_NAME, "rating").text.strip()
            rating = rating.count('★') + 0.5 * rating.count('½')
        except:
            rating = 0

        movielist.loc[len(movielist)] = {type:label, 'filmid':filmid, 'rating':rating}
        movies.loc[len(movies)] = {'filmid':filmid, 'slug':slug}
        
    # remove reting from movielist
    if type == 'list':
        movielist.drop(columns=['rating'], inplace=True)


    # quit driver to avoid bot detection
    driver.quit()

    return movielist, movies


def get_new_records(new_values, old_values):
    """Returns rows in new_values that do not exist in old_values"""
    # 1. Merge the two dataframes on all common columns
    # 2. Use indicator=True to track which dataframe the row came from
    # 3. Use how='left' to keep all rows from new_values
    merged = new_values.merge(
        old_values, 
        how='left', 
        indicator=True
    )
    
    # Filter for rows that only exist in the 'left' (new_values) dataframe
    diff = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge'])
    
    return diff


def drop_outdated_ratings(all_ratings, new_ratings):
    """
    Removes rows from all_ratings that are already present in new_ratings
    based on 'user' and 'filmid'.
    """
    # Merge with an indicator to identify matches
    merged = all_ratings.merge(
        new_ratings[['user', 'filmid']], 
        on=['user', 'filmid'], 
        how='left', 
        indicator=True
    )
    
    # Keep only the rows that weren't found in scraped_ratings
    filtered_df = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge'])
    
    return filtered_df



def main():
    '''Web scrapes letterboxd film ratings for specified users'''

    # constants
    YEAR = '2026'
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

    # read current data
    all_watchlist = pd.read_csv('data\\watchlist.csv')
    all_ratings = pd.read_csv('data\\ratings.csv')
    all_movies = pd.read_csv('data\\movies.csv')
    all_noms = pd.read_csv('data\\noms.csv')

    # initialize empty dataframes
    new_watchlist = pd.DataFrame(columns=['list','filmid'])
    new_ratings = pd.DataFrame(columns=['user','filmid','rating'])
    new_movies = pd.DataFrame(columns=['filmid', 'slug'])
    new_noms = pd.DataFrame(columns=['list','filmid','best_pic'])

    # scrape user ratings
    for user in USERS:
        for page in [1]:#range(14,0,-1):
            
            # scrape movie poster page
            user_url = f'https://letterboxd.com/{user[1]}/films/by/date/page/{page}/'
            scraped_ratings, scraped_movies = scrape('user', user[0], user_url)
            print(f'Scraped: {user[1]}    page: {page}    movies: {len(scraped_ratings)}')

            new_ratings = pd.concat([scraped_ratings, new_ratings])
            new_movies = pd.concat([scraped_movies, new_movies]).drop_duplicates()

    all_ratings = drop_outdated_ratings(all_ratings, new_ratings) # expunge outdated ratings
    new_ratings = get_new_records(new_ratings, all_ratings) # only include unsaved ratings

    # scrape watchlist
    # watchlist_url = 'https://letterboxd.com/_branzino/list/oscars-2026/'
    # scraped_watchlist, scraped_movies = scrape('list', YEAR, watchlist_url)
    # new_watchlist = get_new_records(new_watchlist, all_watchlist) # only include unsaved watchlist
    # new_movies = pd.concat([scraped_movies, new_movies]).drop_duplicates()

    # scrape noms
    # noms_url = 'https://letterboxd.com/000_leo/list/oscars-2026-1/'
    # new_noms, scraped_movies = scrape('list', YEAR, noms_url)
    # new_noms['best_pic'] = 0            # assume nom is not best pic
    # new_noms.loc[:9, "best_pic"] = 1    # set first 10 films in list to best pic
    # new_movies = pd.concat([scraped_movies, new_movies]).drop_duplicates()

    # only include unsved movies
    new_movies = get_new_records(new_movies, all_movies) # only include unsaved ratings

    # write new data if present
    if not new_watchlist.empty:
        all_watchlist = pd.concat([new_watchlist, all_watchlist])
        all_watchlist.to_csv('data\\watchlist.csv', index=False)
        print('\nAdded to watchlist:')
        print(new_watchlist)
    elif not new_ratings.empty:
        all_ratings = pd.concat([new_ratings, all_ratings])
        all_ratings.to_csv('data\\ratings.csv', index=False)
        print('\nAdded to ratings:')
        print(new_ratings)
    elif not new_movies.empty:
        all_movies = pd.concat([new_movies, all_movies])
        all_movies.to_csv('data\\movies.csv', index=False)
        print('\nAdded to movies:')
        print(new_movies)
    elif not all_noms.empty:
        all_noms = pd.concat([new_noms, all_noms])
        all_noms.to_csv('data\\noms.csv', index=False)
        print('\nAdded to noms:')
        print(new_noms)


    # write combined data to csv


if __name__ == '__main__':
    main()

