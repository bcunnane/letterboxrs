from time import sleep
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def setup_driver():
  # Setup Chrome WebDriver
  options = webdriver.ChromeOptions()
  # options.add_argument('--headless')
  options.add_argument('--no-sandbox')
  options.add_argument('--disable-dev-shm-usage')

  # Add a User-Agent to mimic a real browser
  options.add_argument(
      'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
      ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124'
      ' Safari/537.36'
  )

  service = Service(ChromeDriverManager().install())
  return webdriver.Chrome(service=service, options=options)


def scrape(type, label, url):
  '''webscrape letterboxd film data'''
  movielist = pd.DataFrame(columns=[type, 'filmid', 'rating'])
  movies = pd.DataFrame(columns=['filmid', 'slug'])

  scraping = {'user': 'griditem', 'list': 'posteritem'}

  driver = setup_driver()
  driver.get(url)

  try:
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'film-poster'))
    )
  except Exception:
    print(f'ERROR: class film-poster not present at {url}')
    return None

  posters = driver.find_elements(By.CLASS_NAME, scraping[type])

  for poster in posters:
    viewing_p = poster.find_element(By.CLASS_NAME, 'poster-viewingdata')
    uid_string = viewing_p.get_attribute('data-item-uid')  # "film:14093"
    filmid = str(uid_string.split(':')[-1])  # Ensure filmid is explicitly str

    react_data = poster.find_element(By.CLASS_NAME, 'react-component')
    slug = react_data.get_attribute('data-item-slug')

    try:
      rating = poster.find_element(By.CLASS_NAME, 'rating').text.strip()
      rating = rating.count('★') + 0.5 * rating.count('½')
    except Exception:
      rating = 0

    movielist.loc[len(movielist)] = {
        type: label,
        'filmid': filmid,
        'rating': rating,
    }
    movies.loc[len(movies)] = {'filmid': filmid, 'slug': slug}

  if type == 'list':
    movielist.drop(columns=['rating'], inplace=True)

  driver.quit()
  return movielist, movies


def main():
  '''Web scrapes letterboxd film ratings for specified users'''

  YEAR = '2026'
  max_page = 1
  USERS = [
      ('BC', '_branzino'),
      ('CA', 'honeydijon2'),
      ('DN', 'nbditsd'),
      ('KH', 'shewasak8rgrl'),
      ('MF', 'mfrye'),
      ('MT', 'michelletreiber'),
      ('NB', 'NikkiBerry'),
      ('RZ', 'BOBBY_ZEE'),
      ('TA', 'tarias'),
  ]

  all_watchlist = pd.read_csv('data/watchlist.csv', dtype={'filmid': str})
  all_ratings = pd.read_csv('data/ratings.csv', dtype={'filmid': str})
  all_movies = pd.read_csv('data/movies.csv', dtype={'filmid': str})
  all_noms = pd.read_csv('data/noms.csv', dtype={'filmid': str})

  new_watchlist = pd.DataFrame(columns=['list', 'filmid'])
  new_ratings = pd.DataFrame(columns=['user', 'filmid', 'rating'])
  new_movies = pd.DataFrame(columns=['filmid', 'slug'])
  new_noms = pd.DataFrame(columns=['list', 'filmid', 'best_pic'])

  # Scrape user ratings
  for user in USERS:
    for page in range(1, max_page + 1):
      user_url = (
          f'https://letterboxd.com/{user[1]}/films/by/rated-date/page/{page}/'
      )
      scraped_ratings, scraped_movies = scrape('user', user[0], user_url)
      print(
          f'Scraped: {user[1]}    page: {page}    movies:'
          f' {len(scraped_ratings)}'
      )

      new_ratings = pd.concat([scraped_ratings, new_ratings])
      new_movies = pd.concat([scraped_movies, new_movies]).drop_duplicates(
          subset=['filmid'], keep='first'
      )
      sleep(60)

  if not new_ratings.empty:
    all_ratings = pd.concat([new_ratings, all_ratings], ignore_index=True)
    all_ratings = all_ratings.drop_duplicates(subset=['user', 'filmid'], keep='first')
    all_ratings.to_csv('data/ratings.csv', index=False)

  if not new_movies.empty:
    all_movies = pd.concat([new_movies, all_movies], ignore_index=True)
    all_movies = all_movies.drop_duplicates(subset=['filmid'], keep='first')
    all_movies.to_csv('data/movies.csv', index=False)

  if not new_watchlist.empty:
    all_watchlist = pd.concat([new_watchlist, all_watchlist], ignore_index=True)
    all_watchlist = all_watchlist.drop_duplicates(subset=['list', 'filmid'], keep='first')
    all_watchlist.to_csv('data/watchlist.csv', index=False)

  if not new_noms.empty:
    all_noms = pd.concat([new_noms, all_noms], ignore_index=True)
    all_noms = all_noms.drop_duplicates(subset=['list', 'filmid'], keep='first')
    all_noms.to_csv('data/noms.csv', index=False)


if __name__ == '__main__':
  main()