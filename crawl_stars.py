import os
import time
import logging
from typing import List, Dict, Any
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import psycopg2
from psycopg2.extras import execute_values

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GitHub GraphQL endpoint
GITHUB_ENDPOINT = "https://api.github.com/graphql"

# Query to fetch repos (search for any repos, broad query to get variety)
SEARCH_QUERY = gql("""
query SearchRepos($query: String!, $first: Int!, $after: String) {
  search(query: $query, type: REPOSITORY, first: $first, after: $after) {
    repositoryCount
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        ... on Repository {
          nameWithOwner
          stargazerCount
        }
      }
    }
  }
}
""")

def get_github_client(token: str) -> Client:
    """Create GraphQL client with auth."""
    headers = {"Authorization": f"Bearer {token}"}
    transport = RequestsHTTPTransport(url=GITHUB_ENDPOINT, headers=headers)
    return Client(transport=transport, fetch_schema_from_transport=True)

def fetch_repos(client: Client, target_count: int = 100000) -> List[Dict[str, Any]]:
    """Fetch repos using pagination, respect rate limits."""
    repos = []
    query = "language:*"  # Broad query for any repos
    first = 100
    after = None
    fetched = 0

    while fetched < target_count:
        try:
            params = {"query": query, "first": first, "after": after}
            result = client.execute(SEARCH_QUERY, variable_values=params)
            edges = result["search"]["edges"]
            for edge in edges:
                repo = edge["node"]
                repos.append({
                    "name_with_owner": repo["nameWithOwner"],
                    "stargazer_count": repo["stargazerCount"]
                })
                fetched += 1
                if fetched >= target_count:
                    break

            page_info = result["search"]["pageInfo"]
            if not page_info["hasNextPage"] or fetched >= target_count:
                break
            after = page_info["endCursor"]

            # Check rate limit (simple sleep to respect ~5000 points/hour)
            time.sleep(1)  # Adjust if needed

        except Exception as e:
            logger.error(f"Error fetching: {e}")
            time.sleep(60)  # Retry after 1 min
            continue

    logger.info(f"Fetched {len(repos)} repos")
    return repos

def upsert_repos_to_db(repos: List[Dict[str, Any]], db_host: str, db_port: int, db_name: str, db_user: str, db_pass: str):
    """UPSERT repos into Postgres (efficient update)."""
    conn = psycopg2.connect(
        host=db_host, port=db_port, dbname=db_name, user=db_user, password=db_pass
    )
    cur = conn.cursor()

    # Prepare data for UPSERT
    data = [
        (repo["name_with_owner"], repo["stargazer_count"])
        for repo in repos
    ]

    # UPSERT query (update stars if exists, insert if new)
    upsert_query = """
    INSERT INTO repositories (name_with_owner, stargazer_count, updated_at)
    VALUES %s
    ON CONFLICT (name_with_owner)
    DO UPDATE SET
        stargazer_count = EXCLUDED.stargazer_count,
        updated_at = CURRENT_TIMESTAMP
    """
    execute_values(cur, upsert_query, data)
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Upserted {len(data)} repos to DB")

if __name__ == "__main__":
    token = os.getenv("GITHUB_TOKEN")  # From env in Actions
    if not token:
        raise ValueError("GITHUB_TOKEN required")

    client = get_github_client(token)
    repos = fetch_repos(client)
    # DB details from Actions env
    upsert_repos_to_db(
        repos,
        db_host=os.getenv("POSTGRES_HOST", "localhost"),
        db_port=int(os.getenv("POSTGRES_PORT", 5432)),
        db_name=os.getenv("POSTGRES_DB", "postgres"),
        db_user=os.getenv("POSTGRES_USER", "postgres"),
        db_pass=os.getenv("POSTGRES_PASSWORD", "")
    )