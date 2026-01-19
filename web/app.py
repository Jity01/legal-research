"""
Flask web application for legal case search
"""

import logging
import sys
import os
from flask import Flask, render_template, request, jsonify
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.similarity_matcher import SimilarityMatcher
from strategy.citation_extractor import CitationExtractor
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
similarity_matcher = SimilarityMatcher(max_workers=5, use_llm=True, cases_per_batch=10, db_batch_size=50)
citation_extractor = CitationExtractor()


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
        limit = data.get("limit")  # Optional - None means return all matches

        if not query:
            return jsonify({"error": "Query is required"}), 400

        logger.info(
            f"Search query: {query}, filter: {filter_direction}, limit: {limit}"
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
