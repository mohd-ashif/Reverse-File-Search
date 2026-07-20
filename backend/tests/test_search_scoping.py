from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.models.chunk import FileChunk
from app.models.file import FileIndexStatus, FileType, IndexedFile
from app.models.folder import MonitoredFolder
from app.schemas.search import SearchQuery
from app.services.search_service import SearchService


def _create_folder(db_session: Session, path: str = "/tmp/folder") -> MonitoredFolder:
    folder = MonitoredFolder(path=path)
    db_session.add(folder)
    db_session.flush()
    return folder


def _create_file(db_session: Session, folder: MonitoredFolder, filename: str = "sample.txt") -> IndexedFile:
    file_record = IndexedFile(
        folder_id=folder.id,
        absolute_path=f"/tmp/{filename}",
        filename=filename,
        extension=".txt",
        file_type=FileType.TXT,
        size_bytes=10,
        checksum="deadbeef",
        mtime=0.0,
        status=FileIndexStatus.EMBEDDED,
    )
    db_session.add(file_record)
    db_session.flush()
    return file_record


def _add_chunk(db_session: Session, file: IndexedFile, index: int, chroma_id: str) -> FileChunk:
    chunk = FileChunk(file_id=file.id, chunk_index=index, chroma_id=chroma_id, char_count=10)
    db_session.add(chunk)
    db_session.flush()
    return chunk


# --- retrieve() folder scoping ---


def test_retrieve_passes_folder_id_as_where_filter(db_session: Session) -> None:
    folder = _create_folder(db_session)
    file_record = _create_file(db_session, folder)

    embedding_service = MagicMock()
    embedding_service.embed.return_value = [[0.1, 0.2]]

    vector_store = MagicMock()
    vector_store.query.return_value = {
        "ids": [["chunk-a"]],
        "documents": [["some text"]],
        "metadatas": [[{"file_id": file_record.id}]],
        "distances": [[0.1]],
    }

    service = SearchService(db_session, embedding_service=embedding_service, vector_store=vector_store)
    results = service.retrieve("find invoices", top_k=5, folder_id=folder.id)

    vector_store.query.assert_called_once_with([0.1, 0.2], top_k=5, where={"folder_id": folder.id})
    assert len(results) == 1
    assert results[0].file_id == file_record.id


def test_retrieve_without_folder_id_passes_no_where_filter(db_session: Session) -> None:
    embedding_service = MagicMock()
    embedding_service.embed.return_value = [[0.1, 0.2]]
    vector_store = MagicMock()
    vector_store.query.return_value = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    service = SearchService(db_session, embedding_service=embedding_service, vector_store=vector_store)
    service.retrieve("anything", top_k=5)

    vector_store.query.assert_called_once_with([0.1, 0.2], top_k=5, where=None)


# --- retrieve_file() single-file scoping ---


def test_retrieve_file_returns_chunks_in_order_without_similarity_search(db_session: Session) -> None:
    folder = _create_folder(db_session)
    file_record = _create_file(db_session, folder)
    _add_chunk(db_session, file_record, index=1, chroma_id="chunk-1")
    _add_chunk(db_session, file_record, index=0, chroma_id="chunk-0")

    vector_store = MagicMock()
    vector_store.get_by_ids.return_value = {
        "ids": ["chunk-0", "chunk-1"],
        "documents": ["first part", "second part"],
    }

    service = SearchService(db_session, vector_store=vector_store)
    results = service.retrieve_file(file_record.id)

    assert [r.chunk_text for r in results] == ["first part", "second part"]
    assert all(r.file_id == file_record.id and r.score is None for r in results)


def test_retrieve_file_returns_empty_for_unknown_file(db_session: Session) -> None:
    vector_store = MagicMock()
    service = SearchService(db_session, vector_store=vector_store)
    assert service.retrieve_file(999_999) == []
    vector_store.get_by_ids.assert_not_called()


def test_retrieve_file_caps_total_characters(db_session: Session) -> None:
    folder = _create_folder(db_session)
    file_record = _create_file(db_session, folder)
    _add_chunk(db_session, file_record, index=0, chroma_id="chunk-0")
    _add_chunk(db_session, file_record, index=1, chroma_id="chunk-1")

    vector_store = MagicMock()
    vector_store.get_by_ids.return_value = {
        "ids": ["chunk-0", "chunk-1"],
        "documents": ["x" * 30_000, "should be dropped"],
    }

    service = SearchService(db_session, vector_store=vector_store)
    results = service.retrieve_file(file_record.id)

    assert len(results) == 1
    assert results[0].chunk_text == "x" * 30_000


# --- retrieve_for_query() branching ---


def test_retrieve_for_query_prefers_file_id_over_folder_id(db_session: Session) -> None:
    folder = _create_folder(db_session)
    file_record = _create_file(db_session, folder)
    _add_chunk(db_session, file_record, index=0, chroma_id="chunk-0")

    vector_store = MagicMock()
    vector_store.get_by_ids.return_value = {"ids": ["chunk-0"], "documents": ["file content"]}

    service = SearchService(db_session, vector_store=vector_store)
    query = SearchQuery(query="who signed?", folder_id=folder.id, file_id=file_record.id)
    rewritten_query, results = service.retrieve_for_query(query)

    assert rewritten_query == "who signed?"
    assert [r.chunk_text for r in results] == ["file content"]
    vector_store.query.assert_not_called()
