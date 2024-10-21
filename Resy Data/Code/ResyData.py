import pandas as pd
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import os
from openpyxl import load_workbook

count = 5000
# List of US state abbreviations
us_state_abbreviations = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", 
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", 
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", 
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", 
    "WI", "WY"
}

# Helper function to extract venue ID from intercepted API requests
def intercept_and_extract_venue_id(page, venue_url):
    venue_id = None
    found_venue_id = False  # This flag will prevent multiple extractions

    # Define an event handler to capture network requests and look for the venue ID
    def handle_request(request):
        nonlocal venue_id, found_venue_id
        if "https://api.resy.com/2/config?venue_id=" in request.url and not found_venue_id:
            print(f"Intercepted request URL: {request.url}")
            match = re.search(r'venue_id=(\d+)', request.url)
            if match:
                venue_id = match.group(1)
                found_venue_id = True  # Set the flag to True to prevent further extractions
                print(f"Extracted venue ID: {venue_id}")

    # Add the request interception event handler
    page.on("request", handle_request)

    # Visit the venue page
    page.goto(venue_url)
    
    # Wait for the network request (adjust as necessary to ensure the page fully loads)
    page.wait_for_load_state("networkidle")
    
    return venue_id

# Helper function to extract city and state from the href
def extract_city_state(href):
    pattern = r"cities/([a-z-]+)-([a-z]{2})/venues"
    match = re.search(pattern, href)
    if match:
        city = match.group(1).replace('-', ' ').title()  # Convert to readable city name
        state = match.group(2).upper()  # Get the state abbreviation
        return city, state
    return None, None

# Save data to Excel with separate sheets for each city and check if data is written
def save_data_to_excel(state, city, restaurant_data):
    # Prepare the filename for the state
    file_name = f"{state}.xlsx"
    
    # Create the dataframe
    df = pd.DataFrame(restaurant_data)

    # Check if the dataframe is empty before proceeding
    if df.empty:
        print(f"No data to save for {city}, {state}.")
        return False  # Nothing written

    # If the file exists, append to the city sheet (or create if it doesn't exist)
    if os.path.exists(file_name):
        with pd.ExcelWriter(file_name, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            try:
                existing_data = pd.read_excel(file_name, sheet_name=city)
                df = pd.concat([existing_data, df], ignore_index=True)
            except ValueError:  # Sheet does not exist yet
                pass
            df.to_excel(writer, sheet_name=city, index=False)
    else:
        # If the file doesn't exist, create a new file with the city sheet
        with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=city, index=False)

    print(f"Data written to {city}, {state}.")
    return True  # Data was written

# Scrape function using Playwright and BeautifulSoup
def scrape_resy():
    global count
    us_data = {}
    data_written = False  # Flag to check if any data was written

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Set headless to False to see the browser working
        page = browser.new_page()
        page.goto('https://resy.com/list-venues?amp;seats=2&seats=2&date=2024-10-09')
        
        # Give time for the page to load
        page.wait_for_load_state('networkidle', timeout=60000)

        # Extract page content
        content = page.content()

        # Parse the page content with BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        venue_list = soup.find_all('a', class_='venue')

        print(f"Found {len(venue_list)} venues.")
        total_count = len(venue_list)
        for venue in venue_list[count:10000]:
            count += 1
            print(f'Processing url {count} of {total_count-10000}')
            venue_name = venue.get_text(strip=True)
            href = venue.get('href')
            
            # Extract city and state
            city, state = extract_city_state(href)

            if state and state in us_state_abbreviations:
                venue_link = f"https://resy.com/{href}"
                
                # Extract venue ID from intercepted API requests
                venue_id = intercept_and_extract_venue_id(page, venue_link)
                
                print(f"US Venue: {venue_name}, City: {city}, State: {state}, Venue ID: {venue_id}")
                
                if state not in us_data:
                    us_data[state] = {}
                if city not in us_data[state]:
                    us_data[state][city] = []

                # Append data to the list for saving
                us_data[state][city].append({
                    'Restaurant Name': venue_name,
                    'Link': venue_link,
                    'Venue ID': venue_id
                })

                # Save the data to Excel with separate sheets for each city
                if save_data_to_excel(state, city, [{'Restaurant Name': venue_name, 'Link': venue_link, 'Venue ID': venue_id}]):
                    data_written = True  # Update the flag if data was written
            else:
                print(f"Skipping non-US venue: {venue_name}")
        
        browser.close()

    return data_written  # Return if any data was written

if __name__ == "__main__":
    while True:
        try:
            if scrape_resy():
                print("Data successfully written.")
            else:
                print("No data written during this session.")
            break
        except Exception as e:
            print(f"Error occurred: {e}. Retrying...")
            continue
