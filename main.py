"""
gitdash/main.py

# Pre-requisites

The `GH_TOKEN` is a personal access token that can be generated from the GitHub website.

<YOUR_PERSONAL_ACCESS_TOKEN>: minimum requirements — `admin:org`, `admin:public_key`,
`repo`.

To generate it, follow these steps:

* Log in to your GitHub account and go to your settings.
* In the left-side menu, click on Developer Settings.
* Click on Personal Access Tokens.
* Click on Generate new token.
* Provide a name for your token and select the scopes that you need.
* Click on Generate token.

You will only be able to see the token once. Make sure to save it in a safe place.

[See also]
(https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github)
"""

import os
from typing import Any, Iterable, TextIO

import requests
from dotenv import load_dotenv  # `python-dotenv`
from requests import Response


def fmt_repo_field(repository: Any, field: str) -> str:
    max_str_len = 80  # Desired Markdown list item length(to clamp long descriptions.)
    repo_val = repository[field]

    match field:
        case "name":
            return f"[{repo_val}]({repository['html_url']})"
        case "language", "size":
            return f"`{repo_val}`"
        case "license" if repo_val:
            return f"`{repo_val['spdx_id']}`"
        case _ if ((repo_val is not None) and (len(f"{repo_val}") > max_str_len)):
            return f"`{repo_val[:max_str_len]}...`"
        case _:
            return f"`{repo_val}`"


def main() -> None:
    load_dotenv()

    gh_username: str = os.getenv("GH_USERNAME")
    gh_token: str = os.getenv("GH_TOKEN")
    gh_repo_fields: list[str] = ["name", "language", "size", "license", "description"]

    api_url = f"https://api.github.com/users/{gh_username}/repos"
    api_headers: dict[str, str] = {
        "X-GitHub-Api-Version": "2022-11-28",
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {gh_token}",
    }

    page = 1
    all_repos: list[Any] = []

    while True:
        params: dict[str, int] = {"page": page, "per_page": 100}

        response: Response = requests.get(url=api_url, params=params, headers=api_headers)

        if response.status_code == 200:
            gh_repos: Iterable[Any] = response.json()
            if not gh_repos:
                break

            page += 1
            all_repos.extend(gh_repos)
        else:
            print("failed to retrieve repositories. Status code:", response.status_code)  # 401
            break

    out_buffer: list[str] = [f"__{','.join(gh_repo_fields)}__\n"]

    for repo in all_repos:
        if not repo["archived"]:
            item: list[str] = [fmt_repo_field(repository=repo, field=field) for field in gh_repo_fields]
            out_buffer.append(f"* {','.join(item)}\n")

    with open("out.md", "w", encoding="utf-8") as out_file:
        out_file.writelines(out_buffer)


if __name__ == '__main__':
    main()
