"""
test_chunking_service.py – Unit Tests für chunk_text()

Tests:
- leerer Text -> leere Liste
- Text kuerzer als CHUNK_SIZE -> genau ein Chunk
- Text mit mehreren Chunks -> korrekte Chunk-Anzahl und korrekte Overlap-Berechnung
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pytest
from app.services.chunking_service import chunk_text


class TestChunkText:

    def test_empty_text(self):
        """Leerer Text gibt eine leere Liste zurück."""
        result = chunk_text("")
        assert result == []

    def test_text_shorter_than_chunk_size(self):
        """Text kürzer als CHUNK_SIZE gibt genau einen Chunk zurück."""
        text = "Dies ist ein kurzer Text."
        result = chunk_text(text)
        assert len(result) == 1
        assert result[0] == text

    def test_multiple_chunks_with_overlap(self):
        """Text mit mehreren Chunks zeigt korrekte Chunk-Anzahl und korrekten Overlap."""
        # Durchnummerierte statt identische Woerter ("word0", "word1", ...): mit
        # identischen Tokens waere der Overlap-Vergleich immer trivial wahr, egal ob
        # die Slicing-Indizes tatsaechlich stimmen -- so prueft er echte Positionen.
        words = [f"word{i}" for i in range(500)]
        text = " ".join(words)

        result = chunk_text(text)

        # CHUNK_SIZE=400, CHUNK_OVERLAP=50 (Konfig-Default): Chunk 1 = word0..word399,
        # Chunk 2 = word350..word499, danach stoppt die Schleife (naechster Start waere
        # 700, >= 500 Woerter).
        assert len(result) == 2
        assert result[0] == " ".join(words[0:400])
        assert result[1] == " ".join(words[350:500])

        overlap_size = 50
        for i in range(len(result) - 1):
            overlap_from_current = result[i].split()[-overlap_size:]
            overlap_from_next = result[i + 1].split()[:overlap_size]
            assert overlap_from_current == overlap_from_next, (
                f"Overlap zwischen Chunk {i} und {i + 1} nicht korrekt"
            )
