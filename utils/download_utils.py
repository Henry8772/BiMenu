import requests
import os

def is_downloadable(url):
    """
    Does the url contain a downloadable resource?
    """
    h = requests.head(url, allow_redirects=True)
    header = h.headers
    content_type = header.get('content-type')
    if 'html' in content_type.lower():
        return False
    return True

def download_file(url, local_filename):
    """
    Download a file from a given URL. If the file already exists, it doesn't overwrite it.
    """
    # Check if the file already exists
    if os.path.exists(local_filename):
        print(f"File '{local_filename}' already exists. Skipping download.")
        return local_filename  # Return the path of the existing file

    # If the file doesn't exist, proceed with downloading
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                f.write(chunk)
    return local_filename

def download_by_menu_data(food_menus, download_path):
    for link in food_menus:
        file_url = link['reference']
        if is_downloadable(file_url):
            # Extracting the filename from the URL
            filename = os.path.join(download_path, file_url.rsplit('/', 1)[1])
            try:
                # Downloading the file
                download_file(file_url, filename)
                print(f"File '{filename}' downloaded successfully.")
            except Exception as e:
                print(f"Failed to download the file. Error: {e}")
        else:
            print(f"Skipping non-downloadable link: {file_url}")