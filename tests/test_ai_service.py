import pytest
from unittest.mock import patch, MagicMock
from app.services.chunking_service import embed_document


def test_embed_document_returns_stats():
    """
    Testet, dass embed_document() Chunks erstellt, für jeden Chunk ein
    Embedding erzeugt und Statistiken für gültigen Text zurückgibt.
    """
    document_id = 999
    text = "Dies ist ein Testtext für das Embedding."
    mock_embedding_vector = [0.1, 0.2, 0.3, 0.4, 0.5]

    # Mocking der create_embedding Funktion verhindert echte API-Aufrufe an OpenAI.
    with patch('app.services.chunking_service.create_embedding') as mock_create_embedding, \
         patch('app.services.chunking_service.client', MagicMock()):
        mock_create_embedding.return_value = mock_embedding_vector

        mock_db = MagicMock()

        result = embed_document(document_id, text, mock_db)

        assert isinstance(result, dict), "Das Ergebnis sollte ein Dictionary sein."
        assert result['chunks_created'] == 1
        assert result['embedding_model'] == "text-embedding-3-small"
        assert 'elapsed_seconds' in result
        mock_create_embedding.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


def test_embed_document_returns_error_without_client():
    """
    Testet, dass embed_document() einen Fehler zurückgibt, wenn kein
    OpenAI-Client konfiguriert ist, statt einen API-Aufruf zu versuchen.
    """
    mock_db = MagicMock()

    with patch('app.services.chunking_service.client', None):
        result = embed_document(999, "Beliebiger Text", mock_db)

    assert result == {"chunks_created": 0, "error": "OpenAI client not configured"}
    mock_db.add.assert_not_called()
