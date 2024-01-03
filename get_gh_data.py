#!/usr/bin/env python3

from __future__ import annotations
import argparse
import csv
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from github import BadCredentialsException, Github, UnknownObjectException

APP_VERSION = "2024.01.2"

app_name = Path(__file__).name
app_title = f"{app_name} (v{APP_VERSION})"

run_dt = datetime.now(timezone.utc)
run_ts = run_dt.astimezone().strftime("%Y%m%d_%H%M%S")


class AppOptions(NamedTuple):
    key_file: Path
    data_path: Path


def get_args(argv):
    ap = argparse.ArgumentParser(
        description="Queries the GitHub API for metadata about a user's "
        "repositories and saves it into CSV files."
    )

    ap.add_argument(
        "-k",
        "--key-file",
        dest="keyfile",
        action="store",
        help="Name of the file containing the GitHub Personal Access Token "
        "needed to query the API.",
    )

    return ap.parse_args(argv[1:])


def get_opts(argv) -> AppOptions:
    args = get_args(argv)

    if args.keyfile:
        key_file = Path(args.keyfile).expanduser().resolve()
    else:
        # TODO: Document default key-file path (or don't have one).
        key_file = (
            Path("~/KeepLocal/get_gh_data-settings.txt").expanduser().resolve()
        )

    if not key_file.exists():
        sys.stderr.write(f"\nERROR: Cannot find '{key_file}'.\n")
        sys.exit(1)

    # TODO: Make data_path an arg?
    data_path = Path.cwd() / "data"
    if not data_path.exists():
        data_path.mkdir()

    return AppOptions(key_file, data_path)


def get_key(key_file: Path) -> str:
    with key_file.open() as f:
        lines = f.readlines()
    for line in lines:
        s = line.strip()
        if s.startswith("key") and "=" in s:
            return s.split("=")[1].strip().strip('"')
    return None


def get_repos_data(g: Github):
    repos = []
    langs = []
    topics = []

    # -- For debugging other parts, uncomment the 'return' line to not hit the
    #    API and return empty lists.
    #
    # return repos, langs, topics

    print("Reading GitHub API.")

    for repo in g.get_user().get_repos("all"):
        try:
            license_data = repo.get_license()
            license_name = license_data.license.name
        except UnknownObjectException:
            license_name = "(none)"

        fork_parent = repo.parent.html_url if repo.fork else ""

        repos.append(
            {
                "name": repo.name,
                "private": repo.private,
                "description": repo.description,
                "full_name": repo.full_name,
                "html_url": repo.html_url,
                "license_name": license_name,
                "fork": repo.fork,
                "fork_parent": fork_parent,
            }
        )

        repo_langs = repo.get_languages()
        for lang_name, code_bytes in repo_langs.items():
            langs.append(
                {
                    "repo_name": repo.name,
                    "lang_name": lang_name,
                    "code_bytes": code_bytes,
                }
            )

        repo_topics = repo.get_topics()
        for topic in repo_topics:
            topic_dict = {"repo_name": repo.name, "topic": topic}
            topics.append(topic_dict)

    return repos, langs, topics


def write_repos_data(data_path: Path, repos: list[dict]):
    repos_csv = data_path / run_ts / "github-repos.csv"

    print(f"Writing '{repos_csv}'.")

    with repos_csv.open("w", newline="") as f:
        flds = [
            "name",
            "private",
            "description",
            "full_name",
            "html_url",
            "license_name",
            "fork",
            "fork_parent",
        ]
        writer = csv.DictWriter(f, fieldnames=flds, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in repos:
            writer.writerow(row)

    repos_cp = data_path / repos_csv.name
    print(f"Copy to '{repos_cp}'.")
    shutil.copyfile(repos_csv, repos_cp)


def write_langs_data(data_path: Path, langs: list[dict]):
    langs_csv = data_path / run_ts / "github-langs.csv"

    print(f"Writing '{langs_csv}'.")

    with langs_csv.open("w", newline="") as f:
        flds = ["repo_name", "lang_name", "code_bytes"]
        writer = csv.DictWriter(f, fieldnames=flds, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in langs:
            writer.writerow(row)

    langs_cp = data_path / langs_csv.name
    print(f"Copy to '{langs_cp}'.")
    shutil.copyfile(langs_csv, langs_cp)


def write_topics_data(data_path: Path, topics: list[dict]):
    topics_csv = data_path / run_ts / "github-topics.csv"

    print(f"Writing '{topics_csv}'.")
    with topics_csv.open("w", newline="") as f:
        flds = ["repo_name", "topic"]
        writer = csv.DictWriter(f, fieldnames=flds, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in topics:
            writer.writerow(row)

    topics_cp = data_path / topics_csv.name
    print(f"Copy to '{topics_cp}'.")
    shutil.copyfile(topics_csv, topics_cp)


def write_session_data(data_path: Path):
    session_csv = data_path / run_ts / "session.csv"

    print(f"Writing '{session_csv}'.")

    with session_csv.open("w", newline="") as f:
        flds = ["run_date_time", "app_title"]
        writer = csv.DictWriter(f, fieldnames=flds, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        row = {
            "run_date_time": run_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "app_title": app_title,
        }
        writer.writerow(row)

    session_cp = data_path / session_csv.name
    print(f"Copy to '{session_cp}'.")
    shutil.copyfile(session_csv, session_cp)


def main(argv):
    print(f"\n{app_title}\n")

    opts = get_opts(argv)

    key = get_key(opts.key_file)
    if key is None:
        sys.stderr.write(f"\nAccess key not found in '{opts.key_file}'\n")
        sys.exit(1)

    g = Github(key)
    key = None

    try:
        print(f"Accessing '{g.get_user().html_url}'.")
    except BadCredentialsException:
        print(
            "\nERROR: Credentials not accepted.\n\nHas the personal access "
            "token expired?\n\nLook under 'GitHub Profile / Settings / "
            "Developer Settings.\n\n"
        )
        return 1

    repos, langs, topics = get_repos_data(g)

    Path(opts.data_path / run_ts).mkdir()

    write_repos_data(opts.data_path, repos)
    write_langs_data(opts.data_path, langs)
    write_topics_data(opts.data_path, topics)
    write_session_data(opts.data_path)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
