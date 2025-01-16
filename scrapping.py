import os
import requests
import csv
import re
from bs4 import BeautifulSoup
import pickle

# Base directory to store all data
base_dir = 'US_States_Criminal_Data_1'
if not os.path.exists(base_dir):
    os.makedirs(base_dir)

# Save and load state for resuming
state_file = os.path.join(base_dir, 'scraping_state.pkl')

if os.path.exists(state_file):
    with open(state_file, 'rb') as file:
        scraping_state = pickle.load(file)
else:
    scraping_state = {}

def save_scraping_state():
    with open(state_file, 'wb') as file:
        pickle.dump(scraping_state, file)

def create_csv_file(state_name, county_name):
    """Create a CSV file for each county."""
    county_csv_path = os.path.join(base_dir, state_name, county_name, f"{state_name}_{county_name}_data.csv")
    if not os.path.exists(county_csv_path):
        os.makedirs(os.path.dirname(county_csv_path), exist_ok=True)
        with open(county_csv_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Name', 'Profile URL', 'State', 'County'])  # CSV headers
    return county_csv_path

# A set to track profile URLs and avoid duplicates
seen_urls = scraping_state.get('seen_urls', set())

def scrape_criminal_image(profile_url, save_dir, name):
    """Scrape the criminal's image from the profile page and save it."""
    response = requests.get(profile_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the criminal's image
        img_tag = soup.find('img', class_='hidden-narrow', itemprop='url')  # Updated logic for scraping image
        if img_tag:
            img_url = img_tag['src']
            img_name = re.sub(r'[^\w\s-]', '', name).replace(' ', '_') + ".jpg"  # Clean filename
            img_path = os.path.join(save_dir, img_name)

            try:
                img_response = requests.get(img_url, stream=True, timeout=10)
                if img_response.status_code == 200:
                    # Save the image
                    with open(img_path, 'wb') as img_file:
                        for chunk in img_response.iter_content(1024):
                            img_file.write(chunk)
                    print(f"Image saved for {name}: {img_path}")
                    return img_path  # Return the saved image path
                else:
                    print(f"Failed to download image for {name}, URL: {img_url}")
            except Exception as e:
                print(f"Error downloading image for {name}: {e}")
        else:
            print(f"No image found on profile page: {profile_url}")
    else:
        print(f"Failed to load profile page: {profile_url}")
    return None

def scrape_profile_page(url, state_name, county_name, county_csv_path):
    """Scrape individual criminal profiles from a profile page."""
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Capture all profile links with the .html extension
        profiles = soup.find_all('a', href=re.compile(r'.*\.html$'))
        print(f"Profiles found on page: {len(profiles)}")
        if not profiles:
            return []

        data = []
        for profile in profiles:
            try:
                name = profile.find('div', class_='label').text.strip()
                relative_page_url = profile['href']
                page_url = f"https://mugshots.com{relative_page_url}"

                # Only add profiles that haven't been processed before
                if page_url in seen_urls:
                    continue
                seen_urls.add(page_url)

                print(f"Processing profile URL: {page_url}")
                
                county_dir = os.path.join(base_dir, state_name, county_name)
                if not os.path.exists(county_dir):
                    os.makedirs(county_dir)

                # Scrape the criminal's image from the profile page
                img_path = scrape_criminal_image(page_url, county_dir, name)

                if img_path:
                    # Appending the profile data to the list
                    data.append([name, page_url, state_name, county_name])
                    print(f"Data added for {name}: {data[-1]}")  # Debug: Print the added data

            except Exception as e:
                print(f"Error extracting profile info for {profile}: {e}")
                continue

        if data:  # Only write to CSV if there is data
            print(f"Writing {len(data)} profiles to CSV.")
            with open(county_csv_path, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerows(data)
            print(f"Profiles written to {county_csv_path}")
        else:
            print("No data to write to CSV.")
    else:
        print(f"Failed to retrieve the page: {url}")

def get_next_page_url(soup):
    """Find the next page URL if it exists."""
    next_button = soup.find('a', class_='next page')
    if next_button:
        return f"https://mugshots.com{next_button['href']}"
    return None

def scrape_alphabetical_pages(county_url, state_name, county_name, county_csv_path):
    """Scrape all criminal profiles from alphabetical pages in a county."""
    for prefix in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        if (state_name, county_name, prefix) in scraping_state.get('completed_prefixes', set()):
            print(f"Skipping already scraped prefix: {prefix}")
            continue

        alphabet_page_url = f"{county_url}?name_prefix={prefix}"
        print(f"Scraping page for prefix: {prefix}, URL: {alphabet_page_url}")

        current_url = alphabet_page_url
        while current_url:
            scrape_profile_page(current_url, state_name, county_name, county_csv_path)

            response = requests.get(current_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            next_page_url = get_next_page_url(soup)
            current_url = next_page_url if next_page_url else None

        scraping_state.setdefault('completed_prefixes', set()).add((state_name, county_name, prefix))
        save_scraping_state()

def scrape_county_page(county_url, state_name, county_name, county_csv_path):
    """Scrape all criminal profiles from a county page."""
    print(f"Scraping county: {county_name}, URL: {county_url}")
    scrape_alphabetical_pages(county_url, state_name, county_name, county_csv_path)

def scrape_state_page(state_url, state_name):
    """Scrape all counties and their criminal profiles from a state's page."""
    state_dir = os.path.join(base_dir, state_name)
    if not os.path.exists(state_dir):
        os.makedirs(state_dir)

    response = requests.get(state_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Adjusted regular expression to include areas like Unsorted, Borough, District, etc.
        county_links = soup.find_all('a', href=re.compile('^/US-States/[A-Za-z-]+/[A-Za-z-]+(?:-[A-Za-z]+)*'))
        print(f"Found {len(county_links)} counties or areas to scrape in {state_name}.")

        for county_link in county_links:
            county_name = county_link.text.strip()
            county_url = f"https://mugshots.com{county_link['href']}"

            if (state_name, county_name) in scraping_state.get('completed_counties', set()):
                print(f"Skipping already scraped county/area: {county_name}")
                continue

            county_csv_path = create_csv_file(state_name, county_name)
            scrape_county_page(county_url, state_name, county_name, county_csv_path)

            scraping_state.setdefault('completed_counties', set()).add((state_name, county_name))
            save_scraping_state()

def scrape_all_states(states_url):
    """Scrape all U.S. states and their criminal profiles."""
    response = requests.get(states_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        state_links = soup.find_all('a', href=re.compile('^/US-States/[A-Za-z-]+'))
        print(f"Found {len(state_links)} states to scrape.")

        
        state_links = state_links[:] 

        for state_link in state_links:
            state_name = state_link.text.strip()
            state_url = f"https://mugshots.com{state_link['href']}"

            if state_name in scraping_state.get('completed_states', set()):
                print(f"Skipping already scraped state: {state_name}")
                continue

            scrape_state_page(state_url, state_name)

            scraping_state.setdefault('completed_states', set()).add(state_name)
            save_scraping_state()

# Start scraping
states_url = 'https://mugshots.com/US-States/'
scrape_all_states(states_url)

print("Scraping completed.")
