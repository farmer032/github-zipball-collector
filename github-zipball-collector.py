import argparse
import logging
import os
import shutil
import sys
import time
from abc import abstractmethod
from typing import List, Dict, Any

# Type aliases
JSON = Dict[str, Any]


class HttpClient:
    @abstractmethod
    def request_for_json(self, url: str) -> JSON: ...

    @abstractmethod
    def download_file(self, url: str, directory: str, repository_name: str) -> None: ...


try:
    import requests


    class RequestsHttpClient(HttpClient):
        def request_for_json(self, url: str) -> JSON:
            return requests.get(url).json()

        def download_file(self, url: str, directory: str, repository_name: str) -> None:
            request_for_file = requests.get(url, stream=True)
            if request_for_file.status_code == 200:
                with open(os.path.join(directory, repository_name + '.zip'), 'wb') as f:
                    request_for_file.raw.decode_content = True
                    shutil.copyfileobj(request_for_file.raw, f)


    http_client = RequestsHttpClient()

except ImportError as e:
    print(f"Unable to initialize requests http client, {str(e)}")
    print("Fallback to urllib client...")

    from urllib import request
    import json


    class UrllibHttpClient(HttpClient):

        def request_for_json(self, url: str) -> JSON:
            return json.load(request.urlopen(url))

        def download_file(self, url: str, directory: str, repository_name: str) -> None:
            request.urlretrieve(url, os.path.join(directory, repository_name + '.zip'))


    http_client = UrllibHttpClient()

logging.basicConfig(stream=sys.stdout,
                    level=logging.DEBUG,
                    format="%(message)s")


def parse_username_arg() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument('-username', required=True, dest='username')
    args = parser.parse_args()
    user = args.username
    logging.debug(f"Got username {user}")
    return user


def create_directory_if_not_exist(user: str) -> str:
    directory = f"{user}-Date_{time.strftime('%Y-%m-%d')}-Time_{time.strftime('%H-%M-%S')}"
    abs_path = os.path.abspath(directory)
    if not os.path.exists(abs_path):
        logging.info(f"Creating directory {abs_path}")
        os.makedirs(abs_path)

    return abs_path


def request_for_public_repositories(user: str) -> List[JSON]:
    all_pages_content = []
    page_index = 0
    while page := request_for_page(user, page_index):
        all_pages_content += page
        page_index += 1
    return all_pages_content


def request_for_page(user: str, page: int) -> JSON:
    current_page = http_client.request_for_json(
        f"https://api.github.com/users/{user}/repos?per_page=100&page={page}")

    return current_page


def save_repositories(repositories: List[JSON], directory: str) -> None:
    for repository in repositories:
        repository_name = repository['name']
        html_url = repository['html_url']
        zipball_url = f"{html_url}/zipball/master/"
        logging.info(f"Saving repository {repository_name} to {directory}")
        http_client.download_file(zipball_url, directory, repository_name)


def print_received_repositories(repositories: List[JSON]) -> None:
    logging.info("Got public repositories: ")
    for repository in repositories:
        logging.info(f"Public repository: {repository['name']}")


def main(user: str) -> None:
    logging.info(f"Http client: {http_client}")
    target_directory = create_directory_if_not_exist(user)
    logging.info(f"Saving zipball archives in following directory: {target_directory}")
    repositories = request_for_public_repositories(user)
    print_received_repositories(repositories)
    save_repositories(repositories, target_directory)
    logging.info("Completed")


if __name__ == '__main__':
    username = parse_username_arg()
    main(username)
