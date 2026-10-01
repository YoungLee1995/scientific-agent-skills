"""Commands for the deterministic document intake used in Chapter 7."""

from __future__ import annotations

import argparse
import os
import uuid
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from app.services.ingestion import download_open_access_articles, ingest_jats_xml


def connection() -> psycopg.Connection:
    load_dotenv(Path(".env"))
    database_url = os.environ["DATABASE_URL"].replace("+psycopg", "")
    return psycopg.connect(database_url)


def seed_demo(args: argparse.Namespace) -> None:
    organization_id = uuid.UUID(args.organization_id)
    with connection() as conn, conn.cursor() as cursor:
        for name in (
            "student",
            "research-assistant",
            "pi",
            "finance-approver",
            "admin",
        ):
            cursor.execute(
                "INSERT INTO roles (id, name) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                (uuid.uuid4(), name),
            )
        cursor.execute(
            "SELECT id FROM projects WHERE organization_id = %s AND name = %s",
            (organization_id, args.project_name),
        )
        row = cursor.fetchone()
        if row:
            project_id = row[0]
        else:
            project_id = uuid.uuid4()
            cursor.execute(
                "INSERT INTO projects (id, organization_id, name, status) VALUES (%s, %s, %s, 'active')",
                (project_id, organization_id, args.project_name),
            )
    print(project_id)


def download(args: argparse.Namespace) -> None:
    manifest = download_open_access_articles(args.query, Path(args.output), args.limit)
    print(manifest)


def ingest(args: argparse.Namespace) -> None:
    with connection() as conn:
        document_id, created = ingest_jats_xml(
            conn,
            Path(args.source),
            uuid.UUID(args.project),
            args.allowed_role,
            args.classification,
        )
    print(f"{document_id} {'created' if created else 'duplicate'}")


def list_documents(args: argparse.Namespace) -> None:
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, title, version, status, sha256 FROM documents WHERE project_id = %s ORDER BY title",
            (uuid.UUID(args.project),),
        )
        for row in cursor.fetchall():
            print("\t".join(str(value) for value in row))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    seed = commands.add_parser("seed-demo", help="create the roles and a demo project")
    seed.add_argument("--project-name", default="mouse-neuro-demo")
    seed.add_argument(
        "--organization-id", default="00000000-0000-0000-0000-000000000001"
    )
    seed.set_defaults(handler=seed_demo)

    fetch = commands.add_parser(
        "download-open-access", help="download PMC open-access JATS XML"
    )
    fetch.add_argument(
        "--query",
        required=True,
        help="Europe PMC query expression without source filters",
    )
    fetch.add_argument("--output", default="data/inbox")
    fetch.add_argument("--limit", type=int, default=20)
    fetch.set_defaults(handler=download)

    ingest_parser = commands.add_parser(
        "ingest", help="ingest one authorized JATS XML article"
    )
    ingest_parser.add_argument("--project", required=True, help="project UUID")
    ingest_parser.add_argument("--source", required=True)
    ingest_parser.add_argument("--classification", required=True)
    ingest_parser.add_argument("--allowed-role", action="append", required=True)
    ingest_parser.set_defaults(handler=ingest)

    documents = commands.add_parser("documents", help="list project documents")
    document_commands = documents.add_subparsers(
        dest="documents_command", required=True
    )
    list_parser = document_commands.add_parser("list")
    list_parser.add_argument("--project", required=True)
    list_parser.set_defaults(handler=list_documents)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
