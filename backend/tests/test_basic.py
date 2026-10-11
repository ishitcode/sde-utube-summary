from app.services.retrieval_service import retrieve_segments
from app.services.summarization_service import summarize_transcript
from app.services.video_service import extract_video_id, validate_youtube_url


def test_validate_youtube_url_accepts_standard_and_short_links():
    assert validate_youtube_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ') == 'dQw4w9WgXcQ'
    assert validate_youtube_url('https://youtu.be/dQw4w9WgXcQ') == 'dQw4w9WgXcQ'
    assert validate_youtube_url('https://youtube.com/shorts/dQw4w9WgXcQ?feature=share') == 'dQw4w9WgXcQ'


def test_extract_video_id_rejects_invalid_input():
    try:
        extract_video_id('https://example.com/not-youtube')
    except ValueError:
        return
    assert False, 'Expected ValueError for non-YouTube URLs'


def test_extract_video_id_handles_query_params():
    assert extract_video_id('https://www.youtube.com/watch?v=abc123XYZ&feature=share') == 'abc123XYZ'


def test_retrieve_segments_prioritizes_relevant_transcript_text():
    segments = [
        {'text': 'This lecture explains how a linked list differs from an array.', 'start': 0.0, 'end': 15.0},
        {'text': 'Binary search repeatedly splits a sorted array in half to find the target value.', 'start': 15.0, 'end': 32.0},
        {'text': 'The algorithm checks the middle element before moving left or right.', 'start': 32.0, 'end': 48.0},
    ]

    results = retrieve_segments('binary search sorted array', segments, limit=2)
    assert results
    assert 'binary search' in results[0]['text'].lower()
    assert results[0]['score'] > 0


def test_summarize_transcript_extracts_topic_focused_concepts():
    segments = [
        {'text': 'Binary search works efficiently on sorted arrays by checking the middle element.', 'start': 0.0, 'end': 10.0},
        {'text': 'The algorithm repeatedly halves the search space until it finds the target value.', 'start': 10.0, 'end': 20.0},
        {'text': 'This reduces time complexity from linear scanning to logarithmic work.', 'start': 20.0, 'end': 30.0},
    ]

    summary = summarize_transcript(segments)
    assert summary['quick_summary']
    assert any('binary' in concept.lower() for concept in summary['key_concepts'])
    assert summary['timestamp_references']


def test_rag_service_persists_and_retrieves_context_for_a_video():
    from app.services.rag_service import RAGService

    rag = RAGService(storage_path=':memory:')
    segments = [
        {'text': 'Binary search works by repeatedly splitting a sorted array in half.', 'start': 0.0, 'end': 10.0},
        {'text': 'A hash table stores values in buckets for constant-time lookups.', 'start': 10.0, 'end': 20.0},
    ]

    rag.index_video('rag-video', segments)
    hits = rag.search('binary search sorted array', video_id='rag-video', limit=3)
    assert hits
    assert 'binary search' in hits[0]['text'].lower()
