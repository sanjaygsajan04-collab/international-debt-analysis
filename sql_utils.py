"""Small helpers shared by create_views.py and run_queries.py."""
import getpass
import re

import mysql.connector

DB_NAME = "international_debt"


def connect():
    """Ask for the MySQL password and connect to the international_debt database."""
    password = getpass.getpass("MySQL password: ")
    return mysql.connector.connect(host="localhost", user="root", password=password, database=DB_NAME)


def read_statements(path):
    """Split a .sql file into (query_id, sql) pairs.

    Header comments like '-- B1. question' give the id. Other comment lines are dropped.
    These files contain no triggers, so splitting on ';' is safe.
    """
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    keep = [ln for ln in lines
            if not ln.strip().startswith("--") or re.match(r"--\s[BIA]\d+\.", ln.strip())]
    result, current_id = [], None
    for chunk in "\n".join(keep).split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        header = re.match(r"--\s([BIA]\d+)\.\s*(.*)", chunk)
        if header:
            current_id = header.group(1)
        sql = re.sub(r"^--.*\n?", "", chunk, flags=re.M).strip()
        if sql and not sql.upper().startswith("USE "):
            result.append((current_id, sql))
    return result


def read_titles(path):
    """Return {query_id: question} from the '-- B1. question' header lines."""
    titles = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            header = re.match(r"--\s([BIA]\d+)\.\s*(.*)", line.strip())
            if header:
                titles[header.group(1)] = header.group(2)
    return titles
