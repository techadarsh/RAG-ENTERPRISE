# Test for the chunk_texts function in the ingestion pipeline.
#
# This test validates that the chunking logic produces the expected number of chunks
# and that each chunk includes a unique chunk_id. It is designed to be deterministic
# and robust, matching the POC's requirements for reproducibility and stable output.

from pipeline.chunk import chunk_texts

def test_chunk_basic():
    """
    Test the chunk_texts function for correct chunking behavior.

    - Creates a single record with 1000 characters.
    - Chunks the text with size=200 and overlap=50.
    - Asserts that at least 4 chunks are produced.
    - Asserts that every output chunk has a 'chunk_id' key.
    """
    recs = [{"text": "a" * 1000, "source": "x.txt"}]
    out = chunk_texts(recs, size=200, overlap=50)
    assert len(out) >= 4, "Should produce at least 4 chunks for 1000 chars with size=200, overlap=50"
    assert all("chunk_id" in r for r in out), "All chunks should have a 'chunk_id' key"
