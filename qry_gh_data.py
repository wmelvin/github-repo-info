#!/usr/bin/env python3

import csv

from pathlib import Path
from typing import List


APP_VERSION = '2023.12.1'

app_name = Path(__file__).name
app_title = f"{app_name} (v{APP_VERSION})"

repos_csv = Path.cwd() / "data" / "github-repos.csv"

langs_csv = Path.cwd() / "data" / "github-langs.csv"

topics_csv = Path.cwd() / "data" / "github-topics.csv"


def get_repos_data():
    header = None
    data = []
    print(f"Reading '{repos_csv}'.")
    with open(repos_csv) as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        for row in reader:
            data.append(row)
    return header, data


def get_langs_data():
    header = None
    data = []
    print(f"Reading '{langs_csv}'.")
    with open(langs_csv) as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        for row in reader:
            data.append(row)
    return header, data


def get_topics_data():
    header = None
    data = []
    print(f"Reading '{topics_csv}'.")
    with open(topics_csv) as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        for row in reader:
            data.append(row)
    return header, data


def get_public(repos):
    result = []
    for repo in repos:
        if repo["private"] == "False":
            result.append(repo)
    return result


def get_private(repos):
    result = []
    for repo in repos:
        if repo["private"] == "True":
            result.append(repo)
    return result


def get_repo_langs(repo_name: str, langs_all: List[dict]) -> List[dict]:
    result = []

    repo_langs = []
    for lang in langs_all:
        if lang["repo_name"] == repo_name:
            repo_langs.append(lang)

    total_bytes = sum(int(x["code_bytes"]) for x in repo_langs)

    for lang in repo_langs:
        lang_bytes = int(lang["code_bytes"])
        pct = round((lang_bytes / total_bytes) * 100, 2)
        lang["code_pct"] = pct
        result.append(lang)

    return result


def get_langs_str(repo_langs: List[dict]) -> str:
    s = ""
    pct_sum = 0
    for lang in repo_langs:
        pct = round(lang["code_pct"], 1)
        if 1 <= pct:
            pct_sum += pct
            s += f"{lang['lang_name']} {pct}%, "
    if s:
        if pct_sum <= 99:
            s += f"Other {round(100 - pct_sum, 1)}%"
        else:
            s = s[:-2]
    return s


def write_csv_repos_pub(out_path, repos_pub, langs_data):
    out_file = out_path / "repos-public.csv"
    print(f"Writing '{out_file}'.")
    flds = [
        "name",
        "private",
        "description",
        "html_url",
        "prog_langs",
        "license_name",
        "fork",
        "fork_parent",
    ]
    with open(out_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=flds, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for repo in repos_pub:
            row = repo.copy()
            repo_langs = get_repo_langs(repo["name"], langs_data)
            langs_str = get_langs_str(repo_langs)
            row["prog_langs"] = langs_str
            del row["full_name"]
            writer.writerow(row)


def write_csv_repos_pub_md(out_path, repos_pub, langs_data):
    out_file = out_path / "repos-public-md.csv"
    print(f"Writing '{out_file}'.")
    flds = [
        "name",
        "private",
        "description",
        "md_link",
        "prog_langs",
        "license_name",
        "fork",
        "fork_parent",
    ]
    with open(out_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=flds, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for repo in repos_pub:
            row = repo.copy()
            repo_langs = get_repo_langs(repo["name"], langs_data)
            langs_str = get_langs_str(repo_langs)
            row["prog_langs"] = langs_str
            md_link = f"[{repo['full_name']}]({repo['html_url']})"
            row["md_link"] = md_link
            del row["full_name"]
            del row["html_url"]
            del row["fork"]
            del row["fork_parent"]
            writer.writerow(row)


def write_csv_repos_prv(out_path, repos_prv, langs_data):
    out_file = out_path / "repos-private.csv"
    print(f"Writing '{out_file}'.")
    flds = [
        "name",
        "private",
        "description",
        "html_url",
        "prog_langs",
        "license_name",
        "fork",
        "fork_parent",
    ]
    with open(out_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=flds, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for repo in repos_prv:
            repo_langs = get_repo_langs(repo["name"], langs_data)
            langs_str = get_langs_str(repo_langs)
            repo["prog_langs"] = langs_str
            del repo["full_name"]
            writer.writerow(repo)


def write_csv_langs(out_path, repos_data, langs_data):
    out_file = out_path / "repos-langs.csv"

    total_pct_pub = 0
    total_pct_prv = 0
    for repo in repos_data:
        repo_langs = get_repo_langs(repo["name"], langs_data)
        for lang in repo_langs:
            if repo["private"] == "False":
                total_pct_pub += lang["code_pct"]
            else:
                total_pct_prv += lang["code_pct"]

    stats = {}
    for repo in repos_data:
        repo_langs = get_repo_langs(repo["name"], langs_data)
        for lang in repo_langs:
            lang_name = lang["lang_name"]
            if lang_name not in stats.keys():
                stats[lang_name] = {
                    "public_count": 0,
                    "public_pct": 0,
                    "private_count": 0,
                    "private_pct": 0,
                }
            code_pct = lang["code_pct"]
            if repo["private"] == "False":
                stats[lang_name]["public_count"] += 1
                stats[lang_name]["public_pct"] += code_pct / total_pct_pub
            else:
                stats[lang_name]["private_count"] += 1
                stats[lang_name]["private_pct"] += code_pct / total_pct_prv

    print(f"Writing '{out_file}'.")

    flds = [
        "prog_lang",
        "public_count",
        "public_pct",
        "private_count",
        "private_pct",
    ]

    with open(out_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=flds, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for pl, st in stats.items():
            row = {"prog_lang": pl}
            row.update(st)
            writer.writerow(row)


def get_repo_license(repo_name, repos_data):
    result = ""
    for row in repos_data:
        if row["name"] == repo_name:
            result = row["license_name"]
            break
    return result


def write_csv_topics(out_path, repos_data, topics_data):
    rows = []
    for topic in topics_data:
        row = {}
        row["repo_name"] = topic["repo_name"]
        row["topic"] = topic["topic"]
        row["license_name"] = get_repo_license(row["repo_name"], repos_data)
        rows.append(row)

    out_file = out_path / "repos-topics.csv"

    print(f"Writing '{out_file}'.")

    flds = [
        "repo_name",
        "topic",
        "license_name",
    ]

    with open(out_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=flds, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    print(f"\n{app_title}\n")

    _, repos_data = get_repos_data()
    _, langs_data = get_langs_data()
    _, topics_data = get_topics_data()

    out_path = Path.cwd() / "output"
    assert out_path.exists()

    repos_pub = get_public(repos_data)
    repos_prv = get_private(repos_data)

    write_csv_repos_pub(out_path, repos_pub, langs_data)

    write_csv_repos_pub_md(out_path, repos_pub, langs_data)

    write_csv_repos_prv(out_path, repos_prv, langs_data)

    write_csv_langs(out_path, repos_data, langs_data)

    write_csv_topics(out_path, repos_data, topics_data)


if __name__ == "__main__":
    main()
