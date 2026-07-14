"""CLI for managing monitored folders and running the indexing pipeline.

Usage:
    python scripts/indexer_cli.py add-folder <path>
    python scripts/indexer_cli.py remove-folder <folder_id>
    python scripts/indexer_cli.py list-folders
    python scripts/indexer_cli.py scan <folder_id>
    python scripts/indexer_cli.py scan --all
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.services.folder_service import (
    FolderAlreadyMonitoredError,
    FolderNotFoundError,
    FolderService,
    InvalidFolderPathError,
)
from app.services.indexing_pipeline import IndexingPipeline
from app.services.scanner_service import FileScannerService


def add_folder(path: str) -> None:
    with SessionLocal() as db:
        try:
            folder = FolderService(db).add_folder(path)
        except (InvalidFolderPathError, FolderAlreadyMonitoredError) as exc:
            print(f"Error: {exc}")
            return
        print(f"Added folder [{folder.id}] {folder.path}")


def remove_folder(folder_id: int) -> None:
    with SessionLocal() as db:
        try:
            FolderService(db).remove_folder(folder_id)
        except FolderNotFoundError as exc:
            print(f"Error: {exc}")
            return
        print(f"Removed folder {folder_id}")


def list_folders() -> None:
    with SessionLocal() as db:
        for folder in FolderService(db).list_folders():
            print(f"[{folder.id}] {folder.path} (active={folder.is_active})")


def scan(folder_id: int | None) -> None:
    with SessionLocal() as db:
        folder_service = FolderService(db)
        folders = [folder_service.get_folder(folder_id)] if folder_id is not None else folder_service.list_folders()

        for folder in folders:
            scan_result = FileScannerService(db).scan_folder(folder)
            index_result = IndexingPipeline(db).process_pending(folder_id=folder.id)
            print(
                f"Folder [{folder.id}] {folder.path}: "
                f"added={scan_result.added} modified={scan_result.modified} deleted={scan_result.deleted} "
                f"skipped={scan_result.skipped} | extracted={index_result.extracted} "
                f"embedded={index_result.embedded} failed={index_result.failed}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add-folder")
    add_parser.add_argument("path")

    remove_parser = subparsers.add_parser("remove-folder")
    remove_parser.add_argument("folder_id", type=int)

    subparsers.add_parser("list-folders")

    scan_parser = subparsers.add_parser("scan")
    scan_group = scan_parser.add_mutually_exclusive_group(required=True)
    scan_group.add_argument("folder_id", type=int, nargs="?")
    scan_group.add_argument("--all", action="store_true")

    args = parser.parse_args()

    if args.command == "add-folder":
        add_folder(args.path)
    elif args.command == "remove-folder":
        remove_folder(args.folder_id)
    elif args.command == "list-folders":
        list_folders()
    elif args.command == "scan":
        scan(None if args.all else args.folder_id)


if __name__ == "__main__":
    main()
