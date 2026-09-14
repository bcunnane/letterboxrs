import argparse
import random
import re
from time import sleep
import bs4
from curl_cffi import requests
import pandas as pd

USERS = [
    ('BC', '_branzino'),
    # ('CA', 'honeydijon2'),
    # ('DN', 'nbditsd'),
    # ('KH', 'shewasak8rgrl'),
    # ('MF', 'mfrye'),
    # ('MT', 'michelletreiber'),
    # ('NB', 'NikkiBerry'),
    ('RZ', 'BOBBY_ZEE'),
    # ('TA', 'tarias'),
]


def extract_rating(poster):
  '''Extracts star rating numerical value (0.5 - 5.0) from poster container.'''
  container = poster.find_parent('li') or poster.parent or poster
  rating_el = container.select_one(
      'span.rating, p.poster-viewingdata span, span.rating-large'
  )
  if not rating_el:
    return 0.0

  classes = rating_el.get('class', [])
  for cls in classes:
    match = re.match(r'^rated-(\d+)$', cls)
    if match:
      return int(match.group(1)) / 2.0

  data_rating = rating_el.get('data-rating') or container.get('data-rating')
  if data_rating and str(data_rating).isdigit():
    return int(data_rating) / 2.0

  text = rating_el.text.strip()
  if '★' in text or '½' in text:
    return text.count('★') + 0.5 * text.count('½')

  return 0.0


def extract_slug(poster):
  '''Extracts film slug from poster element or its parent container.'''
  parent = poster.parent

  slug = poster.get('data-film-slug') or parent.get('data-film-slug')
  if slug:
    return slug

  link = poster.get('data-target-link') or parent.get('data-target-link')
  if link and '/film/' in link:
    return link.split('/film/')[-1].strip('/')

  anchor = parent.find('a') or poster.find('a')
  if anchor and anchor.get('href'):
    href = anchor.get('href')
    if '/film/' in href:
      return href.split('/film/')[-1].strip('/')

  return None


def _fetch_and_parse_page(url):
  '''Fetches an HTML page using curl_cffi and extracts all (poster, slug, title)

  tuples.
  '''
  response = requests.get(url, impersonate='chrome')

  if response.status_code != 200:
    return response.status_code, []

  soup = bs4.BeautifulSoup(response.text, 'html.parser')
  posters = soup.select('div.film-poster')

  page_items = []
  for poster in posters:
    slug = extract_slug(poster)
    if not slug:
      continue

    img_tag = poster.find('img')
    title = img_tag.get('alt') if img_tag and img_tag.get('alt') else slug

    page_items.append((poster, slug, title))

  return 200, page_items


def scrape_user_ratings(label, username, max_pages=None, is_full_run=False):
  '''Scrapes user rated films using shared page parser.'''
  scraped_data = []
  page = 1

  while True:
    if max_pages and page > max_pages:
      break

    url = f'https://letterboxd.com/{username}/films/by/rated-date/page/{page}/'
    status_code, items = _fetch_and_parse_page(url)

    if status_code != 200:
      if status_code == 404:
        print(f'Reached end of pages for {username} at page {page - 1}.')
      else:
        print(f'ERROR: Received status {status_code} for {url}')
      break

    if not items:
      print(f'No films found on page {page} for {username}. Ending pagination.')
      break

    for poster, slug, _ in items:
      rating = extract_rating(poster)
      scraped_data.append({'user': label, 'slug': slug, 'rating': rating})

    print(f'Scraped Ratings: {username} | Page: {page} | Items: {len(items)}')
    page += 1

    delay = (
        random.uniform(2.0, 4.5) if is_full_run else random.uniform(1.5, 3.5)
    )
    sleep(delay)

  return pd.DataFrame(scraped_data)


def main():
  parser = argparse.ArgumentParser(
      description='Scrape Letterboxd user ratings.'
  )
  parser.add_argument(
      '--full',
      action='store_true',
      help='Perform full backfill across all pages for all users.',
  )
  parser.add_argument(
      '--pages',
      type=int,
      default=1,
      help=(
          'Number of pages to scrape per user (default: 1). Ignored if --full'
          ' is set.'
      ),
  )
  args = parser.parse_args()

  # Update Ratings CSV
  max_pages = None if args.full else args.pages
  ratings_file = 'data/ratings.csv'

  try:
    all_ratings = pd.read_csv(ratings_file, dtype=str)
    all_ratings['rating'] = pd.to_numeric(
        all_ratings['rating'], errors='coerce'
    )
  except FileNotFoundError:
    all_ratings = pd.DataFrame(columns=['user', 'slug', 'rating'])

  new_ratings_list = []
  mode_str = 'FULL BACKFILL' if args.full else f'INCREMENTAL ({args.pages} pg)'
  print(f'\n=== Starting Scrape Mode: {mode_str} ===')

  for label, username in USERS:
    user_df = scrape_user_ratings(
        label, username, max_pages=max_pages, is_full_run=args.full
    )
    if not user_df.empty:
      new_ratings_list.append(user_df)

  if new_ratings_list:
    new_ratings = pd.concat(new_ratings_list, ignore_index=True)

    all_ratings = pd.concat([new_ratings, all_ratings], ignore_index=True)
    all_ratings = all_ratings.drop_duplicates(
        subset=['user', 'slug'], keep='first'
    )

    all_ratings.to_csv(ratings_file, index=False)
    print(
        f'\nSuccessfully updated {ratings_file}. Total records:'
        f' {len(all_ratings)}'
    )
  else:
    print('\nNo data was scraped across any user.')


if __name__ == '__main__':
  main()