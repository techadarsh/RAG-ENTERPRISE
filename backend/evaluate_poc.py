#!/usr/bin/env python3
"""
RAG Chatbot Evaluation Script (Phase 3)
Measures retrieval speed, generation time, and answer relevance.
Results exported to /app/results/results.md for dissertation.
"""

import requests
import time
import json
import os
from typing import Dict, List, Any
from datetime import datetime

# Configuration
API_URL = os.getenv("BACKEND_URL", "http://localhost:8000/ask")
RESULTS_DIR = "/app/results"
RESULTS_FILE = os.path.join(RESULTS_DIR, "results.md")

# Test queries covering various enterprise topics
TEST_QUERIES = [
    "What is the sprint duration?",
    "Explain the agile workflow.",
    "What is the PTO policy?",
    "Describe the engineering standards.",
    "How do we handle incident management?",
    "What are the incident severity levels?",
    "How do I authenticate with the API?",
    "What is the code review process?",
]


def evaluate_query(query: str, query_num: int) -> Dict[str, Any]:
    """
    Evaluate a single query and return performance metrics.
    
    Args:
        query: The query string to test
        query_num: Query number for logging
        
    Returns:
        Dictionary containing metrics and results
    """
    print(f"\n[{query_num}] Evaluating: {query}")
    
    result = {
        "query": query,
        "query_num": query_num,
        "retrieval_ms": None,
        "generation_ms": None,
        "total_ms": None,
        "top_source": None,
        "score": None,
        "answer_preview": None,
        "status": "❌ Failed",
        "error": None
    }
    
    try:
        # Measure total time
        start_time = time.perf_counter()
        
        # Make API request
        response = requests.post(
            API_URL,
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Check response
        if response.status_code != 200:
            result["error"] = f"HTTP {response.status_code}"
            print(f"  ❌ Error: HTTP {response.status_code}")
            return result
        
        data = response.json()
        
        # Extract metrics
        result["total_ms"] = round(total_time, 2)
        result["retrieval_ms"] = data.get("retrieval_time_ms", 0)
        result["generation_ms"] = data.get("generation_time_ms", 0)
        
        # Extract top source and score
        sources = data.get("sources", [])
        if sources:
            top_source = sources[0]
            result["top_source"] = top_source.get("title", "Unknown")
            result["score"] = round(top_source.get("score", 0) * 100, 2)  # Convert to percentage
        
        # Get answer preview (first 100 chars)
        answer = data.get("answer", "")
        result["answer_preview"] = answer[:100] + "..." if len(answer) > 100 else answer
        
        result["status"] = "✅ Success"
        
        print(f"  ✓ Total: {result['total_ms']}ms | Top source: {result['top_source']} ({result['score']}%)")
        
    except requests.Timeout:
        result["error"] = "Request timeout"
        print(f"  ❌ Error: Request timeout")
    except requests.RequestException as e:
        result["error"] = f"Request error: {str(e)}"
        print(f"  ❌ Error: {str(e)}")
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
        print(f"  ❌ Error: {str(e)}")
    
    return result


def write_results_markdown(results: List[Dict[str, Any]]) -> None:
    """
    Write evaluation results to Markdown file.
    
    Args:
        results: List of evaluation result dictionaries
    """
    # Ensure results directory exists
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # Calculate averages (only from successful queries)
    successful_results = [r for r in results if r["status"] == "✅ Success"]
    
    if successful_results:
        avg_retrieval = sum(r["retrieval_ms"] for r in successful_results) / len(successful_results)
        avg_generation = sum(r["generation_ms"] for r in successful_results) / len(successful_results)
        avg_total = sum(r["total_ms"] for r in successful_results) / len(successful_results)
        avg_score = sum(r["score"] for r in successful_results if r["score"]) / len(successful_results)
    else:
        avg_retrieval = avg_generation = avg_total = avg_score = 0
    
    # Write Markdown file
    with open(RESULTS_FILE, "w") as f:
        f.write("# RAG Chatbot Evaluation Results\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Queries**: {len(results)}\n")
        f.write(f"**Successful**: {len(successful_results)}\n")
        f.write(f"**Failed**: {len(results) - len(successful_results)}\n\n")
        
        # Performance Summary
        f.write("## Performance Summary\n\n")
        f.write("| Metric | Average | Unit |\n")
        f.write("|--------|---------|------|\n")
        f.write(f"| Retrieval Time | {avg_retrieval:.2f} | ms |\n")
        f.write(f"| Generation Time | {avg_generation:.2f} | ms |\n")
        f.write(f"| Total Latency | {avg_total:.2f} | ms |\n")
        f.write(f"| Relevance Score | {avg_score:.2f}% | % |\n\n")
        
        # Detailed Results Table
        f.write("## Detailed Results\n\n")
        f.write("| # | Query | Retrieval (ms) | Generation (ms) | Total (ms) | Top Source | Score | Status |\n")
        f.write("|---|-------|----------------|-----------------|------------|------------|-------|--------|\n")
        
        for r in results:
            retrieval = f"{r['retrieval_ms']:.1f}" if r['retrieval_ms'] else "N/A"
            generation = f"{r['generation_ms']:.1f}" if r['generation_ms'] else "N/A"
            total = f"{r['total_ms']:.1f}" if r['total_ms'] else "N/A"
            source = r['top_source'] if r['top_source'] else "N/A"
            score = f"{r['score']:.2f}%" if r['score'] else "N/A"
            
            f.write(f"| {r['query_num']} | {r['query']} | {retrieval} | {generation} | {total} | {source} | {score} | {r['status']} |\n")
        
        # Answer Previews
        f.write("\n## Answer Previews\n\n")
        for r in successful_results:
            f.write(f"### Query {r['query_num']}: {r['query']}\n\n")
            f.write(f"**Answer**: {r['answer_preview']}\n\n")
            f.write(f"**Source**: {r['top_source']} (Relevance: {r['score']:.2f}%)\n\n")
            f.write("---\n\n")
        
        # System Configuration
        f.write("## System Configuration\n\n")
        f.write("- **Backend URL**: `http://localhost:8000/ask`\n")
        f.write("- **Embedding Model**: `all-MiniLM-L6-v2`\n")
        f.write("- **LLM Model**: `mistral:latest`\n")
        f.write("- **Vector DB**: Milvus\n")
        f.write("- **Platform**: Docker (Apple Silicon ARM64)\n\n")
        
        # Notes
        f.write("## Notes\n\n")
        f.write("- Retrieval time includes embedding generation and vector search\n")
        f.write("- Generation time is pure LLM inference time\n")
        f.write("- Total latency is end-to-end response time\n")
        f.write("- Relevance score is cosine similarity of top-ranked source\n")
        f.write("- All measurements in milliseconds (ms)\n\n")


def main():
    """Main evaluation function"""
    print("=" * 70)
    print("RAG CHATBOT EVALUATION - PHASE 3")
    print("=" * 70)
    print(f"API URL: {API_URL}")
    print(f"Test Queries: {len(TEST_QUERIES)}")
    print(f"Results Output: {RESULTS_FILE}")
    print("=" * 70)
    
    # Run evaluation for all queries
    results = []
    for i, query in enumerate(TEST_QUERIES, 1):
        result = evaluate_query(query, i)
        results.append(result)
        time.sleep(0.5)  # Small delay between queries
    
    # Write results to file
    print("\n" + "=" * 70)
    print("WRITING RESULTS TO FILE")
    print("=" * 70)
    write_results_markdown(results)
    print(f"✅ Results saved to: {RESULTS_FILE}")
    
    # Print summary to console
    successful = [r for r in results if r["status"] == "✅ Success"]
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"✅ Successful queries: {len(successful)}/{len(results)}")
    
    if successful:
        avg_retrieval = sum(r["retrieval_ms"] for r in successful) / len(successful)
        avg_generation = sum(r["generation_ms"] for r in successful) / len(successful)
        avg_total = sum(r["total_ms"] for r in successful) / len(successful)
        avg_score = sum(r["score"] for r in successful if r["score"]) / len(successful)
        
        print(f"\n📊 Average Metrics:")
        print(f"   Retrieval Time:  {avg_retrieval:.2f} ms")
        print(f"   Generation Time: {avg_generation:.2f} ms")
        print(f"   Total Latency:   {avg_total:.2f} ms")
        print(f"   Relevance Score: {avg_score:.2f}%")
    
    print("\n" + "=" * 70)
    print(f"📄 Detailed results: {RESULTS_FILE}")
    print("=" * 70 + "\n")
    
    return len(successful) == len(results)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
