# -*- coding: utf-8 -*-

# gitdash/main.py

# `gitdash` generates pretty Markdown lists of git repositories.
#
# # Pre-requisites
# 
# This workflow requires two environment variables: `GH_USERNAME` and
# `GH_TOKEN`. They need to be added as Action secrets in 'Security/Secrets
# and variables/Actions'.
# 
# * `GH_USERNAME` is your GitHub account's username.
# * `GH_TOKEN` is a # personal access token generated from the GitHub website.
# 
# <GH_TOKEN> Personal Access Token(PAT): Minimum Requirements:
# 
# * repo
# * admin:org -> read:org (optional)
# * admin:public_key -> read.public_key (optional)
# * admin:repo_hook -> read:repo_hook (optional)
# * notification (optional)
# * audit_log -> read:audit_log (optional)
# 
# To generate it, follow these steps:
# 
# * Log in to your GitHub account and go to your settings.
# * In the left-side menu, click on Developer Settings.
# * Click on Personal Access Tokens.
# * Click on Generate new token.
# * Provide a name for your token and select the scopes that you need.
# * Click on Generate token.
# 
# You will only see the token once. Make sure to save it in a safe place.
# [See also]
# (https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github)

from os import getenv
from sys import exit, stderr
from typing import Any, Iterable

from dotenv import load_dotenv  # `python-dotenv`.
from requests import get, Response

# ——————————————————————————————————————————————————————————————————————————
# Configuration Constants.
REPO_VISIBILITY = "public"
REPO_AFFILIATION = "owner"
REPO_SORT = "created"
REPO_PER_PAGE = 100  # min: 30, max: 100. Repos to fetch at each GET request.
REPO_IGNORED_KEYS = {"archived", "fork", }  # Must have a `bool` # API value.

# ——————————————————————————————————————————————————————————————————————————
# Desired Repository Property Constants(to emit to markdown.)
OUT_REPO_PARAMS = ["name", "language", "size", "license", "description", ]
OUT_MAX_COL_LEN = 80  # Desired Markdown item length(clamp long descriptions.)

# ——————————————————————————————————————————————————————————————————————————
# CI GitHub Workflow Action specific Constants.
GITDASH_OUTFILE_MD = "out.md"  # Output file path to emit markdown to.
GITDASH_ENV_GH_USERNAME = "GH_USERNAME"  # GitHub account username in `.env`.
GITDASH_ENV_GH_TOKEN = "GH_TOKEN"  # GitHub Personal Access Token in `.env`.

# ——————————————————————————————————————————————————————————————————————————
# GitHub API Constants.
API_BASE_URL = "https://api.github.com"
API_HEADER_VERSION = "2022-11-28"
API_HEADER_ACCEPT = "application/vnd.github+json"
API_STATUS_UNKNOWN_MSG = "Unknown status code"
API_STATUS_OK = 200
API_STATUS_CODES = {
    200: "OK",
    304: "Not modified",
    401: "Forbidden",
    422: "Validation failed, or the endpoint has been spammed.",
}


# Format a repository property based on the provided key.
def fmt_repo(repo: Any, key: str) -> str:
    prop: object = repo[key]
    match key:
        case "name":
            return f"[`{prop}`]({repo['html_url']})"
        case "language", "size":
            return f"`{prop}`"
        case "license" if prop:
            return f"`{prop['spdx_id']}`"
        case _ if (prop is not None and
                   len(f"{prop}") > OUT_MAX_COL_LEN):
            return f"`{prop[:OUT_MAX_COL_LEN]}...`"
        case _:
            return f"`{prop}`"


# Main function fetches user's GitHub repositories,
# and parses it as a pretty list and writes to a Markdown file.
def run() -> None:
    load_dotenv()  # Load environment variables.

    # ——————————————————————————————————————————————————————————————————————————
    # Fetch and parse user's credentials stored as environment variables.
    gh_username: str = getenv(GITDASH_ENV_GH_USERNAME)
    gh_token: str = getenv(GITDASH_ENV_GH_TOKEN)
    if not (gh_token or gh_username):
        print("error: Neither GH_TOKEN nor GH_USERNAME is provided. "
              "Please set at least one environment variable.", file=stderr, )
        exit(1)

    api_headers: dict[str, str] = {
        "X-GitHub-Api-Version": API_HEADER_VERSION,
        "Accept":               API_HEADER_ACCEPT,
    }
    if gh_token:
        api_headers["Authorization"] = f"Bearer {gh_token}"

    api_url: str = (f"{API_BASE_URL}"
                    f"/{'user' if gh_token else f'users/{gh_username}'}"
                    f"/repos")

    # ——————————————————————————————————————————————————————————————————————————
    # Query and collect user's repositories via GET request.
    all_repos: list[Any] = []
    params: dict[str, int | str] = dict(
        page=1, per_page=REPO_PER_PAGE, sort=REPO_SORT,
        visibility=REPO_VISIBILITY, affiliation=REPO_AFFILIATION)

    while True:
        resp: Response = get(url=api_url, params=params,
                             headers=api_headers)
        status = resp.status_code
        if not status == API_STATUS_OK:
            err = API_STATUS_CODES.get(status, __default=API_STATUS_UNKNOWN_MSG)
            print(f"error:({status}): GET request failed: {err}", file=stderr, )
            break

        gh_repos: Iterable[Any] = resp.json()
        if not gh_repos:
            break

        all_repos.extend(gh_repos)
        params['page'] += 1

    # ——————————————————————————————————————————————————————————————————————————
    # Prepare pretty formatted Markdown to write to output file.
    out_buffer: list[str] = list(f"__{','.join(OUT_REPO_PARAMS)}__\n")
    gen_repos = (r for r in all_repos
                 if not any(r[key] for key in REPO_IGNORED_KEYS))

    for repo in gen_repos:
        item = [fmt_repo(repo=repo, key=key) for key in OUT_REPO_PARAMS]
        out_buffer.append(f"* {','.join(item)}\n")

    # ——————————————————————————————————————————————————————————————————————————
    # Write the generated Markdown buffer to output file.
    with open(GITDASH_OUTFILE_MD, "w", encoding="utf-8") as out_file:
        out_file.writelines(out_buffer)


if __name__ == '__main__':
    exit(run())
