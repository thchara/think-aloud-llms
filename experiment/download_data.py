import requests
from bs4 import BeautifulSoup
import os
from tqdm import tqdm
import warnings


def set_up_session(args):

    # Create a session to persist login
    session = requests.Session()

    # Step 1: Fetch the login page to get the CSRF token
    login_page_response = session.get(args["LOGIN_URL"])
    if login_page_response.status_code != 200:
        raise Exception("Failed to load login page.")

    # Parse the login page to extract the CSRF token
    soup = BeautifulSoup(login_page_response.text, "html.parser")
    csrf_token = soup.find("input", {"name": "_token"})["value"]

    # Log in to the website
    login_payload = {
        "email": args["USERNAME"],
        "password": args["PASSWORD"],
        "_token": csrf_token,
    }
    login_response = session.post(
        args["LOGIN_URL"], data=login_payload, allow_redirects=True
    )
    if login_response.status_code == 200:
        print("Login successful.")
    else:
        raise Exception(f"Login failed. Status code: {login_response.status_code}")

    return session


def get_links_from_single_page(soup, session):
    table = soup.find_all("tbody")[0]
    links = []
    for row in table.find_all("tr"):
        # check if the row corresponds to a trial that completed successfully
        succeeded = len(row.find_all(class_="badge-success")) > 0
        if succeeded:
            download_link = row.find_all("a", class_="card-link")[0]
            # If there's a download link, download it
            if "Download data" in download_link.text:
                links.append(download_link["href"])

    return links


def get_download_links(session, args):
    all_download_links = []
    response = session.get(args["CSV_PAGE_URL"])
    page = response.text
    print(f"Reading from {args['CSV_PAGE_URL']}")
    while True:
        soup = BeautifulSoup(page, "html.parser")
        download_links = get_links_from_single_page(soup, session)
        all_download_links.extend(download_links)

        next_buttons = soup.find_all(rel="next")

        # break if there are no more next buttons
        if len(next_buttons) == 0:
            break

        page_link = next_buttons[0]["href"]
        print(f"Reading from {page_link}")
        page = session.get(page_link).text

    return all_download_links


def download_csvs(session, download_links, args):

    # Create download directory if it doesn't exist
    os.makedirs(args["DOWNLOAD_DIR"], exist_ok=True)

    # Download each CSV file
    for link in tqdm(download_links):
        csv_response = session.get(link)
        filename = csv_response.headers["Content-Disposition"].split("filename=")[1]
        file_path = os.path.join(args["DOWNLOAD_DIR"], filename)
        # if os.path.exists(file_path):
        #     print(f"We've already downloaded {filename}. Stopping.")
        #     break

        if csv_response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(csv_response.content)
        else:
            warnings.warn(f"Failed to download {filename}.")


def main(args):
    session = set_up_session(args)

    download_links = get_download_links(session, args)
    download_csvs(session, download_links, args)


if __name__ == "__main__":

    args = {
        "LOGIN_URL": "https://www.cognition.run/login",
        "CSV_PAGE_URL": "https://www.cognition.run/tasks/25716",
        "USERNAME": os.environ["COGNITION_RUN_EMAIL"],
        "PASSWORD": os.environ["COGNITION_RUN_PASSWORD"],
        "DOWNLOAD_DIR": "/scr/verbal-protocol/data/full-experiment",
    }
    main(args)
