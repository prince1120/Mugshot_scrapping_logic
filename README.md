# US States Criminal Data Scraper

This project is a Python-based web scraper designed to gather criminal data from mugshots.com. It scrapes criminal profiles, including images, from various counties across the United States. The data is stored in CSV files organized by state and county, and the images are saved in respective directories for each county.

## Features

- Scrapes criminal profiles and images from mugshots.com for all U.S. states and their counties.
- Stores the criminal profile data in CSV files with information such as name, profile URL, state, and county.
- Saves criminal images to individual directories by state and county.
- Resumes scraping by saving the state of the process (which pages have been scraped) using a pickle file.
- Handles paginated data across alphabetical profile pages.

## Requirements

- Python 3.x
- Libraries:
  - `requests`
  - `beautifulsoup4`
  - `csv`
  - `os`
  - `re`
  - `pickle`

You can install the required libraries using `pip`:

```bash
pip install requests beautifulsoup4
