import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# constants
URLS = {'movies': 'https://letterboxd.com/_branzino/list/oscars-2026/',
        'oscars':'https://letterboxd.com/000_leo/list/oscars-2026-1/'}
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
    movies = pd.DataFrame(columns=['filmid','title', 'slug'])

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
        title = react_data.get_attribute("data-item-name")
        # date = movie.find_element(By.TAG_NAME, "time").get_attribute("datetime")[0:10]
        try:
            rating = poster.find_element(By.CLASS_NAME, "rating").text.strip()
            rating = rating.count('★') + 0.5 * rating.count('½')
        except:
            rating = 0

        movielist.loc[len(movielist)] = {type:label, 'filmid':filmid, 'rating':rating}
        movies.loc[len(movies)] = {'filmid':filmid, 'title':title, 'slug':slug}
        
    # remove reting from movielist
    if type == 'list':
        movielist.drop(columns=['rating'], inplace=True)


    # quit driver to avoid bot detection
    driver.quit()

    return movielist, movies


def scrape_watchlist():
    '''Webscrape yearly watchlist from letterboxd'''

    # read current data
    all_watchlist = pd.read_csv('data\\watchlist.csv')
    all_movies = pd.read_csv('data\\movies.csv')

    # scrape new data
    year = '2026'
    url = 'https://letterboxd.com/_branzino/list/oscars-2026/'
    new_watchlist, new_movies = scrape('list', year, url)

    # combine new and current data
    all_watchlist = pd.concat([new_watchlist, all_watchlist]).drop_duplicates()
    all_movies = pd.concat([new_movies, all_movies]).drop_duplicates()

    # write combined data to csv
    all_watchlist.to_csv('data\\watchlist.csv', index=False)
    all_movies.to_csv('data\\movies.csv', index=False)


def scrape_oscars():
    '''Webscrape oscar nomination list from letterboxd'''

    # read current data
    all_noms = pd.read_csv('data\\noms.csv')
    all_movies = pd.read_csv('data\\movies.csv')

    # scrape new data
    year = '2026'
    url = 'https://letterboxd.com/000_leo/list/oscars-2026-1/'
    new_noms, new_movies = scrape('list', year, url)

    # set first 10 films to best picture (confirm true on letterboxd)
    new_noms['best_pic'] = 0
    new_noms.loc[:9, "best_pic"] = 1

    # combine new and current data
    all_noms = pd.concat([new_noms, all_noms]).drop_duplicates()
    all_movies = pd.concat([new_movies, all_movies]).drop_duplicates()

    # write combined data to csv
    all_noms.to_csv('data\\noms.csv', index=False)
    all_movies.to_csv('data\\movies.csv', index=False)



def main():
    '''Web scrapes letterboxd film ratings for specified users'''


    # all_ratings = pd.read_csv('data\\ratings.csv')
    # all_movies = pd.read_csv('data\\movies.csv')
    
    # page = 1
    # user = USERS[5]
    # url = f'https://letterboxd.com/{user[1]}/films/by/date/page/{page}/'
    
    # new_ratings, new_movies = scrape('user', user[0], url)
    # all_ratings = pd.concat([new_ratings, all_ratings]).drop_duplicates()
    # all_movies = pd.concat([new_movies, all_movies]).drop_duplicates()

    # all_ratings.to_csv('data\\ratings.csv', index=False)
    # all_movies.to_csv('data\\movies.csv', index=False)


    scrape_watchlist()
    # scrape_oscars()



if __name__ == '__main__':
    main()

