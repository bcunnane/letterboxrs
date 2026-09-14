import bs4
from curl_cffi import requests
import pandas as pd

# Replace with the curated Letterboxd Oscars list URL once nominations drop
NOMINATIONS_URL = 'https://letterboxd.com/yurimorgan/list/oscars-2026/'

WATCHLIST_URL = 'https://letterboxd.com/_branzino/list/oscars-2026/'


def build_nominations_csv(output_file='data/noms.csv'):
  page = 1
  nominees = []

  print(f'Fetching nominees from: {NOMINATIONS_URL}')

  while True:
    url = f"{NOMINATIONS_URL.rstrip('/')}/page/{page}/"
    res = requests.get(url, impersonate='chrome')

    if res.status_code != 200:
      if res.status_code == 404:
        print(f'Reached end of list at page {page - 1}.')
      else:
        print(f'Error status {res.status_code} fetching page {page}.')
      break

    soup = bs4.BeautifulSoup(res.text, 'html.parser')
    posters = soup.select('div.film-poster')

    if not posters:
      break

    for poster in posters:
      parent = poster.parent
      slug = poster.get('data-film-slug') or parent.get('data-film-slug')

      if not slug:
        link = poster.get('data-target-link') or parent.get('data-target-link')
        if link and '/film/' in link:
          slug = link.split('/film/')[-1].strip('/')

      if not slug:
        anchor = parent.find('a') or poster.find('a')
        if anchor and anchor.get('href') and '/film/' in anchor['href']:
          slug = anchor['href'].split('/film/')[-1].strip('/')

      if slug:
        # Default all best_pic flags to 0 for manual editing later
        nominees.append({'slug': slug, 'best_pic': 0})

    print(f'Page {page}: Scraped {len(posters)} films.')
    page += 1

  if nominees:
    df = pd.DataFrame(nominees).drop_duplicates(subset=['slug'])
    df.to_csv(output_file, index=False)
    print(
        f'\nSuccessfully saved {len(df)} nominated films to {output_file}'
        ' (all best_pic set to 0).'
    )
  else:
    print('No films were scraped.')


def build_watchlist_csv(output_file='data/watchlist.csv'):
  page = 1
  watchlist_items = []

  print(f'Fetching watchlist from: {WATCHLIST_URL}')

  while True:
    url = f"{WATCHLIST_URL.rstrip('/')}/page/{page}/"
    res = requests.get(url, impersonate='chrome')

    if res.status_code != 200:
      if res.status_code == 404:
        print(f'Reached end of watchlist at page {page - 1}.')
      else:
        print(f'Error status {res.status_code} fetching page {page}.')
      break

    soup = bs4.BeautifulSoup(res.text, 'html.parser')
    posters = soup.select('div.film-poster')

    if not posters:
      break

    for poster in posters:
      parent = poster.parent
      slug = poster.get('data-film-slug') or parent.get('data-film-slug')

      if not slug:
        link = poster.get('data-target-link') or parent.get('data-target-link')
        if link and '/film/' in link:
          slug = link.split('/film/')[-1].strip('/')

      if not slug:
        anchor = parent.find('a') or poster.find('a')
        if anchor and anchor.get('href') and '/film/' in anchor['href']:
          slug = anchor['href'].split('/film/')[-1].strip('/')

      postered_identifier = poster.get('data-postered-identifier') or parent.get(
          'data-postered-identifier'
      )

      if slug:
        watchlist_items.append({
            'slug': slug,
            'data-postered-identifier': postered_identifier,
        })

    print(f'Page {page}: Scraped {len(posters)} watchlist films.')
    page += 1

  if watchlist_items:
    df = pd.DataFrame(watchlist_items).drop_duplicates(subset=['slug'])
    df.to_csv(output_file, index=False)
    print(f'\nSuccessfully saved {len(df)} watchlist films to {output_file}')
  else:
    print('No watchlist films were scraped.')


if __name__ == '__main__':
  build_nominations_csv()
  build_watchlist_csv()
