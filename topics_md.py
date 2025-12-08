#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

APP_VERSION = "2025.12.1"

app_name = Path(__file__).name
app_title = f"{app_name} (v{APP_VERSION})"

repos_csv = Path.cwd() / "data" / "github-repos.csv"

topics_csv = Path.cwd() / "data" / "github-topics.csv"

altnames_csv = Path.cwd() / "input" / "topics_altnames.csv"

run_dt = datetime.now(timezone.utc)


class AppOptions(NamedTuple):
    output_path: Path
    into_file: Path | None


def get_args(arglist=None):
    ap = argparse.ArgumentParser(
        description="Reads GitHub repository metadata from CSV files saved "
        "by get_gh_data.py and writes Markdown files listing 'Repositories "
        "by Topics' and 'Repositories by License'. Can also insert those as "
        "sections into another Markdown document (such as a README.md)."
    )

    ap.add_argument(
        "--insert-into",
        dest="into_file",
        action="store",
        help="Optional. File in which to insert the Markdown sections.",
    )
    # TODO: Add more details to help text.

    ap.add_argument(
        "-o",
        "--output-to",
        dest="outdir",
        action="store",
        help="Directory in which to create output files. Optional. "
        "By default the output is written to a directory named 'output' "
        "under the currrent working directory.",
    )

    return ap.parse_args(arglist)


def get_input_lower(prompt):
    """
    Returns keyboard input as lowercase.

    Having this in a separate function makes it easy to 'monkeypatch'
    for testing.
    """
    return input(prompt).lower()


def get_user_input(prompt, choices, default=None):
    assert len(choices) > 0  # noqa: S101
    assert all(x == x.lower() for x in choices)  # noqa: S101

    while True:
        answer = get_input_lower(prompt)
        if answer == "":
            if default is not None:
                answer = default
                break
        elif answer in choices:
            break

        print("Please select from the list of valid choices.")
    return answer


def get_opts(arglist=None) -> AppOptions:
    args = get_args(arglist)

    if args.outdir:
        outpath = Path(args.outdir).expanduser().resolve()
        if not outpath.exists():
            print(f"Directory does not exist: '{outpath}'")
            if (
                get_user_input(
                    "Would you like to create it?  Enter (Y)es or (n)o: ", "y,n", "y"
                )
                == "y"
            ):
                outpath.mkdir()

        if not outpath.exists():
            sys.stderr.write(f"\nDirectory does not exist: '{outpath}'.\n")
            sys.stderr.write("Cannot continue.\n\n")
            sys.exit(1)

        if not outpath.is_dir():
            sys.stderr.write(f"\nERROR: '{outpath}' is not a directory.\n")
            sys.exit(1)

    else:
        outpath = Path.cwd() / "output"

    if args.into_file:
        into_file = Path(args.into_file)
        if not into_file.exists():
            sys.stderr.write(f"\nERROR: Cannot find '{into_file}'.\n")
            sys.exit(1)
    else:
        into_file = None

    return AppOptions(outpath, into_file)


def get_repos_data():
    header = None
    data = []
    print(f"Reading '{repos_csv}'.")
    with repos_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        data = list(reader)
    return header, data


def get_topics_data():
    header = None
    data = []
    print(f"Reading '{topics_csv}'.")
    with topics_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        data = list(reader)
    return header, data


def get_topics_altnames():
    header = None
    data = []
    print(f"Reading '{altnames_csv}'.")
    with altnames_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        data = list(reader)
    return header, data


def get_public(repos):
    return [repo for repo in repos if repo["private"] == "False"]


def get__public_archived(repos):
    return [
        repo for repo in repos if (
            repo["private"] == "False" and repo["archived"] == "True"
        )
    ]


def get_repos_with_topic(
    topic_name: str, topics: list[dict], repos: list[dict]
) -> list[dict]:
    result = []
    for topic in topics:
        if topic["topic"] == topic_name:
            repo_name = topic["repo_name"]
            for repo in repos:
                if repo["name"] == repo_name:
                    result.append(repo)
                    break
    return result


def get_md_repos_by_topic(topics_data, repos_data):
    all_topics = []
    for t in topics_data:
        if t["topic"] not in all_topics:
            all_topics.append(t["topic"])
    all_topics.sort()

    repos_pub = get_public(repos_data)

    _, alt_names = get_topics_altnames()

    topics_list = []
    for t in all_topics:
        alt_name = t
        for row in alt_names:
            if t == row["topic_name"]:
                alt_name = row["alt_name"]
                break
        topics_list.append((t, alt_name))

    topics_list.sort(key=lambda x: x[1].lower())

    md = []

    md.append("<details>")
    md.append("<summary><b>Repositories by Topic</b></summary>")
    md.append("")
    md.append(
        "*The list below was generated based on the Topics assigned to "
        "each public repository as of "
        f"{run_dt.astimezone().strftime('%Y-%m-%d')}. "
        "Any repository may be under multiple topics.*"
    )
    md.append("")

    #  List archived repositories separately becuase "archived" is an attribute,
    #  not a topic.

    repos_arc = get__public_archived(repos_data)
    if repos_arc:

        md.append(
            f"<details>\n<summary>(Archived) <sup>({len(repos_arc)})</sup>"
            "</summary>\n<ul>"
        )

        for repo in repos_arc:
            is_fork: bool = repo.get("fork") == "True"
            frk = "(fork) " if is_fork else ""

            lic: str = repo.get("license_name")
            lic = lic.replace("(none)", "")
            if lic:
                lic = f" ({lic})"
            a = f'<a href="{repo["html_url"]}">{repo["name"]}</a>'
            md.append(f"<li>{a} {frk}- {repo['description']}{lic}</li>")

        md.append("</ul>\n</details>")

    #  List repositories by Topic.

    for t, descr in topics_list:
        repos = get_repos_with_topic(t, topics_data, repos_pub)
        if repos:
            md.append(
                f"<details>\n<summary>{descr} <sup>({len(repos)})</sup></summary>\n<ul>"
            )

            for repo in repos:
                is_fork: bool = repo.get("fork") == "True"
                frk = "(fork) " if is_fork else ""

                is_archived: bool = repo.get("archived") == "True"
                arc = "(archived) " if is_archived else ""

                lic: str = repo.get("license_name")
                lic = lic.replace("(none)", "")
                if lic:
                    lic = f" ({lic})"
                a = f'<a href="{repo["html_url"]}">{repo["name"]}</a>'
                md.append(f"<li>{a} {arc}{frk}- {repo['description']}{lic}</li>")

            md.append("</ul>\n</details>")

    md.append("</details>")
    md.append(
        f"<!-- Generated {run_dt.strftime('%Y-%m-%d %H:%M %Z')} by {app_title} -->"
    )
    return md


def write_md_repos_by_topic(out_path: Path, topics_data, repos_data):
    md = get_md_repos_by_topic(topics_data, repos_data)
    out_file = out_path / "repos-by-topic.md"
    print(f"Writing '{out_file}'.")
    with out_file.open("w") as f:
        for line in md:
            f.write(f"{line}\n")


def get_md_repos_by_license(repos_data):
    repos_pub = get_public(repos_data)
    licenses = []
    for repo in repos_pub:
        if repo["license_name"] not in licenses:
            licenses.append(repo["license_name"])
    licenses.sort()

    md = []

    md.append("<details>")
    md.append("<summary><b>Repositories by License</b></summary>")
    md.append("")
    md.append(
        "*The list below was generated based on the License assigned to "
        "each public repository as of "
        f"{run_dt.astimezone().strftime('%Y-%m-%d')}.*"
    )
    md.append("")

    md.append("Repositories with no license may be:")
    md.append("- A work-in-progress, which may be given a license when more complete.")
    md.append(
        "- A demo or experiment, available for reference, but not usable as "
        "a library or application."
    )
    md.append("- An infrastructure item (GitHub pages, or this README).")
    md.append("")

    for lic in licenses:
        md.append(f"<details>\n<summary>{lic}</summary>\n<ul>")
        for repo in repos_pub:
            is_fork: bool = repo.get("fork") == "True"
            frk = "(fork) " if is_fork else ""

            is_archived: bool = repo.get("archived") == "True"
            arc = "(archived) " if is_archived else ""

            if repo["license_name"] == lic:
                a = f'<a href="{repo["html_url"]}">{repo["name"]}</a>'
                md.append(f"<li>{a} {arc}{frk}- {repo['description']}</li>")
        md.append("</ul>\n</details>")

    md.append("</details>")
    md.append(
        f"<!-- Generated {run_dt.strftime('%Y-%m-%d %H:%M %Z')} by {app_title} -->"
    )
    return md


def write_md_repos_by_license(out_path: Path, repos_data):
    md = get_md_repos_by_license(repos_data)
    out_file = out_path / "repos-by-license.md"
    print(f"Writing '{out_file}'.")
    with out_file.open("w") as f:
        for line in md:
            f.write(f"{line}\n")


def replace_section(
    begin_tag: str, end_tag: str, in_lines: list[str], section_lines: list[str]
) -> list[str]:
    begin_index = None
    end_index = None

    for i, line in enumerate(in_lines):
        s = line.strip()
        if s == begin_tag:
            begin_index = i
        elif s == end_tag:
            end_index = i

    errs = []
    if begin_index is None:
        errs.append(f"Could not find '{begin_tag}'")

    if end_index is None:
        errs.append(f"Could not find '{end_tag}'")

    if errs:
        msg = "\n".join(errs)
        print(f"Cannot update section.\n{msg} ")
        return in_lines

    if begin_index > end_index:
        raise ValueError("begin_index must be less than end_index")

    lines_before = in_lines[: begin_index + 1]
    lines_after = in_lines[end_index:]

    return [] + lines_before + section_lines + lines_after


def insert_sections(into_file: Path, topics_data, repos_data):
    if into_file is None:
        return

    assert isinstance(into_file, Path)  # noqa: S101

    print(f"Updating '{into_file}'.")
    with into_file.open() as f:
        lines = [s.rstrip() for s in f.readlines()]

    topics_md = get_md_repos_by_topic(topics_data, repos_data)
    lines = replace_section(
        "<!-- Begin_Repositories_by_Topic -->",
        "<!-- End_Repositories_by_Topic -->",
        lines,
        topics_md,
    )

    license_md = get_md_repos_by_license(repos_data)
    lines = replace_section(
        "<!-- Begin_Repositories_by_License -->",
        "<!-- End_Repositories_by_License -->",
        lines,
        license_md,
    )

    into_file.write_text("\n".join(lines))


def main(arglist=None):
    print(f"\n{app_title}\n")

    opts = get_opts(arglist)

    _, repos_data = get_repos_data()
    _, topics_data = get_topics_data()

    write_md_repos_by_topic(opts.output_path, topics_data, repos_data)

    write_md_repos_by_license(opts.output_path, repos_data)

    insert_sections(opts.into_file, topics_data, repos_data)

    return 0


if __name__ == "__main__":
    main()
