"""
Flask web application for legal case search
"""

import logging
import sys
import os
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    Response,
    stream_with_context,
)
from typing import Dict, List, Optional
import json
import queue
import threading

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.similarity_matcher import SimilarityMatcher
from strategy.citation_extractor import CitationExtractor
from strategy.query_parser import QueryParser
from database import get_case_by_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the directory where this file is located
web_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(web_dir, "templates"),
    static_folder=os.path.join(web_dir, "static"),
)

# Initialize components with optimized settings
# Process 10 cases per LLM call with 5 concurrent workers
# Fetches cases in batches of 50 from database
similarity_matcher = SimilarityMatcher(
    max_workers=5, use_llm=True, cases_per_batch=10, db_batch_size=50
)
citation_extractor = CitationExtractor()
query_parser = QueryParser()


@app.route("/")
def index():
    """Main search page"""
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search():
    """Search endpoint"""
    try:
        data = request.get_json()
        query = data.get("query", "")
        filter_direction = data.get("filter_direction")  # 'for_defendant' or None
        # Default to None to search ALL cases - UI will handle pagination
        limit = data.get("limit") if data.get("limit") is not None else None

        if not query:
            return jsonify({"error": "Query is required"}), 400

        logger.info(
            f"Search query: {query}, filter: {filter_direction}, limit: {limit} (None = all cases)"
        )

        # Find similar cases (limit=None means return all matches)
        # Note: Query factors will be logged in similarity_matcher.find_similar_cases()
        results = similarity_matcher.find_similar_cases(
            query=query, limit=limit, filter_direction=filter_direction
        )

        # Enrich with citation data (batch fetch for performance)
        case_ids = [case.get("id") for case in results if case.get("id")]
        citing_cases_map = (
            citation_extractor.get_citing_cases_batch(case_ids) if case_ids else {}
        )

        enriched_results = []
        for case in results:
            case_id = case.get("id")
            citing_cases = citing_cases_map.get(case_id, [])

            case["citing_cases"] = citing_cases
            case["citing_count"] = len(citing_cases)

            enriched_results.append(case)

        return jsonify({"results": enriched_results, "count": len(enriched_results)})

    except Exception as e:
        logger.error(f"Error in search: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/search/stream", methods=["POST"])
def search_stream():
    """Streaming search endpoint that sends results as they're found"""
    try:
        data = request.get_json()
        query = data.get("query", "")
        filter_direction = data.get("filter_direction")
        limit = data.get("limit") if data.get("limit") is not None else None

        if not query:
            return jsonify({"error": "Query is required"}), 400

        logger.info(
            f"Streaming search: {query}, filter: {filter_direction}, limit: {limit}"
        )

        def generate():
            """Generator that yields results as they're found"""
            results_queue = queue.Queue()
            error_occurred = threading.Event()

            def search_worker():
                """Worker thread that performs the search"""
                try:
                    # We need to modify similarity_matcher to support callbacks
                    # For now, do the search and send results in chunks
                    results = similarity_matcher.find_similar_cases(
                        query=query, limit=limit, filter_direction=filter_direction
                    )

                    # Enrich with citation data
                    case_ids = [case.get("id") for case in results if case.get("id")]
                    citing_cases_map = (
                        citation_extractor.get_citing_cases_batch(case_ids)
                        if case_ids
                        else {}
                    )

                    enriched_results = []
                    for case in results:
                        case_id = case.get("id")
                        citing_cases = citing_cases_map.get(case_id, [])
                        case["citing_cases"] = citing_cases
                        case["citing_count"] = len(citing_cases)
                        enriched_results.append(case)

                    # Send results in chunks for progressive display
                    chunk_size = 10
                    for i in range(0, len(enriched_results), chunk_size):
                        chunk = enriched_results[i : i + chunk_size]
                        results_queue.put(("chunk", chunk))

                    results_queue.put(("done", {"count": len(enriched_results)}))
                except Exception as e:
                    logger.error(f"Error in streaming search: {e}", exc_info=True)
                    results_queue.put(("error", str(e)))
                    error_occurred.set()

            # Start search in background thread
            thread = threading.Thread(target=search_worker, daemon=True)
            thread.start()

            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Searching all cases...'})}\n\n"

            # Stream results as they come in
            while True:
                try:
                    msg_type, data = results_queue.get(timeout=1.0)

                    if msg_type == "chunk":
                        yield f"data: {json.dumps({'type': 'results', 'results': data})}\n\n"
                    elif msg_type == "done":
                        yield f"data: {json.dumps({'type': 'done', 'count': data['count']})}\n\n"
                        break
                    elif msg_type == "error":
                        yield f"data: {json.dumps({'type': 'error', 'error': data})}\n\n"
                        break
                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    if error_occurred.is_set():
                        break
                    continue

        return Response(stream_with_context(generate()), mimetype="text/event-stream")

    except Exception as e:
        logger.error(f"Error in streaming search endpoint: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/validate-query", methods=["POST"])
def validate_query():
    """Validate a query and ask clarifying questions if needed"""
    try:
        data = request.get_json()
        query = data.get("query", "")
        previous_answers = data.get("previous_answers", [])

        if not query:
            return jsonify({"error": "Query is required"}), 400

        logger.info(f"Validating query: {query}, previous answers: {previous_answers}")

        # Validate the query
        validation_result = query_parser.validate_query(query, previous_answers)

        return jsonify(validation_result)

    except Exception as e:
        logger.error(f"Error validating query: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/case/<int:case_id>")
def get_case(case_id: int):
    """Get full case details"""
    try:
        case = get_case_by_id(case_id)
        if not case:
            return jsonify({"error": "Case not found"}), 404

        # Get citing cases
        citing_cases = citation_extractor.get_citing_cases(case_id)
        case["citing_cases"] = citing_cases

        return jsonify(case)

    except Exception as e:
        logger.error(f"Error getting case: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
