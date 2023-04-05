#!/usr/bin/env python3

import argparse
import csv
import sys

from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path
from typing import List


APP_VERSION = "230405.1"

app_name = Path(__file__).name
app_title = f"{app_name} (v.{APP_VERSION})"

repos_csv = Path.cwd() / "data" / "github-repos.csv"

topics_csv = Path.cwd() / "data" / "github-topics.csv"

altnames_csv = Path.cwd() / "input" / "topics_altnames.csv"

run_dt = datetime.now(timezone.utc)

AppOptions = namedtuple(
    "AppOptions", "output_path, into_file"
)


def get_args(argv):
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

    return ap.parse_args(argv[1:])


def get_input_lower(prompt):
    """
    Returns keyboard input as lowercase.

    Having this in a separate function makes it easy to 'monkeypatch'
    for testing.
    """
    return input(prompt).lower()


def get_user_input(prompt, choices, default=None):
    assert 0 < len(choices)
    assert all([x == x.lower() for x in choices])
    while True:
        answer = get_input_lower(prompt)
        if answer == "":
            if default is not None:
                answer = default
                break
        else:
            if answer in choices:
                break
        print("Please select from the list of valid choices.")
    return answer


def get_opts(argv) -> AppOptions:
    args = get_args(argv)

    if args.outdir:
        outpath = Path(args.outdir).expanduser().resolve()
        if not outpath.exists():
            print(f"Directory does not exist: '{outpath}'")
            if "y" == get_user_input(
                "Would you like to create it?  Enter (Y)es or (n)o: ",
                "y,n",
                "y"
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
    with open(repos_csv) as f:
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


def get_topics_altnames():
    header = None
    data = []
    print(f"Reading '{altnames_csv}'.")
    with open(altnames_csv) as f:
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


def get_repos_with_topic(
    topic_name: str, topics: List[dict], repos: List[dict]
) -> List[dict]:
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

    md = []

    md.append("<details>")
    md.append("<summary><b>Repositories by Topic</b></summary>")
    md.append("")
    md.append(
        "*The list below was generated based on the Topics assigned to "
        "each public repository as of "
        f"{run_dt.astimezone().strftime('%Y-%m-%d')}.*"
    )
    md.append("")

    for t, descr in topics_list:
        repos = get_repos_with_topic(t, topics_data, repos_pub)
        if repos:
            md.append(f"<details>\n<summary>{descr}</summary>\n<ul>")

            for repo in repos:
                lic: str = repo.get("license_name")
                lic = lic.replace("(none)", "")
                if lic:
                    lic = f" ({lic})"
                a = f'<a href="{repo["html_url"]}">{repo["name"]}</a>'
                md.append(f"<li>{a} - {repo['description']}{lic}</li>")

            md.append("</ul>\n</details>")

    md.append("</details>")
    md.append(
        f"<!-- Generated {run_dt.strftime('%Y-%m-%d %H:%M %Z')} "
        f"by {app_title} -->"
    )
    return md


def write_md_repos_by_topic(out_path: Path, topics_data, repos_data):
    md = get_md_repos_by_topic(topics_data, repos_data)
    out_file = out_path / "repos-by-topic.md"
    print(f"Writing '{out_file}'.")
    with open(out_file, "w") as f:
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
    md.append(
        "- A work-in-progress, which may be given a license when more "
        "complete."
    )
    md.append(
        "- A demo or experiment, available for reference, but not usable as "
        "a library or application."
    )
    md.append("- An infrastructure item (GitHub pages, or this README).")
    md.append("")

    for license in licenses:
        md.append(f"<details>\n<summary>{license}</summary>\n<ul>")
        for repo in repos_pub:
            if repo["license_name"] == license:
                a = f'<a href="{repo["html_url"]}">{repo["name"]}</a>'
                md.append(f"<li>{a} - {repo['description']}</li>")
        md.append("</ul>\n</details>")

    md.append("</details>")
    md.append(
        f"<!-- Generated {run_dt.strftime('%Y-%m-%d %H:%M %Z')} "
        f"by {app_title} -->"
    )
    return md


def write_md_repos_by_license(out_path: Path, repos_data):
    md = get_md_repos_by_license(repos_data)
    out_file = out_path / "repos-by-license.md"
    print(f"Writing '{out_file}'.")
    with open(out_file, "w") as f:
        for line in md:
            f.write(f"{line}\n")


def replace_section(
    begin_tag: str,
    end_tag: str,
    in_lines: List[str],
    section_lines: List[str]
) -> List[str]:

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

    assert begin_index < end_index

    lines_before = in_lines[:begin_index + 1]
    lines_after = in_lines[end_index:]

    return [] + lines_before + section_lines + lines_after


def insert_sections(into_file: Path, topics_data, repos_data):
    if into_file is None:
        return

    assert isinstance(into_file, Path)

    print(f"Updating '{into_file}'.")
    with open(into_file) as f:
        lines = [s.rstrip() for s in f.readlines()]

    topics_md = get_md_repos_by_topic(topics_data, repos_data)
    lines = replace_section(
        "<!-- Begin_Repositories_by_Topic -->",
        "<!-- End_Repositories_by_Topic -->",
        lines,
        topics_md
    )

    license_md = get_md_repos_by_license(repos_data)
    lines = replace_section(
        "<!-- Begin_Repositories_by_License -->",
        "<!-- End_Repositories_by_License -->",
        lines,
        license_md
    )

    into_file.write_text("\n".join(lines))


def main(argv):
    print(f"\n{app_title}\n")

    opts = get_opts(argv)

    _, repos_data = get_repos_data()
    _, topics_data = get_topics_data()

    write_md_repos_by_topic(opts.output_path, topics_data, repos_data)

    write_md_repos_by_license(opts.output_path, repos_data)

    insert_sections(opts.into_file, topics_data, repos_data)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))