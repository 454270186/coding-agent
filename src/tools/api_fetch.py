"""
API Fetch Tool.

Allows agents to fetch data from external APIs before generating code,
avoiding CORS issues by using server-side requests.
"""

import requests
from typing import Dict, Any
from langchain_core.tools import tool


@tool
def fetch_api_data(url: str, method: str = "GET", headers: Dict[str, str] = None, timeout: int = 30) -> Dict[str, Any]:
    """
    Fetch data from an external API using server-side request.

    This tool allows you to fetch real data from APIs before generating code.
    Use this to get actual data that can be embedded as static data in the generated code,
    avoiding CORS issues in browser.

    Args:
        url: The API endpoint URL to fetch from
        method: HTTP method (GET, POST, etc.). Default is GET
        headers: Optional dictionary of HTTP headers
        timeout: Request timeout in seconds. Default is 30

    Returns:
        Dictionary with:
        - success: Boolean indicating if request succeeded
        - data: The response data (text or JSON)
        - status_code: HTTP status code
        - error: Error message if request failed

    Example:
        # Fetch arXiv papers
        result = fetch_api_data(
            url="http://export.arxiv.org/api/query?search_query=cat:cs.AI&max_results=10"
        )
        if result["success"]:
            papers_data = result["data"]
            # Now embed this data in your generated JavaScript code
    """
    if headers is None:
        headers = {}

    try:
        # Make the request
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            timeout=timeout
        )

        # Try to parse as JSON first
        try:
            data = response.json()
            content_type = "json"
        except ValueError:
            # If not JSON, return as text
            data = response.text
            content_type = "text"

        return {
            "success": True,
            "data": data,
            "content_type": content_type,
            "status_code": response.status_code,
            "url": url
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": f"Request timeout after {timeout} seconds",
            "url": url
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Connection error. Check if the URL is correct and accessible",
            "url": url
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}",
            "url": url
        }
