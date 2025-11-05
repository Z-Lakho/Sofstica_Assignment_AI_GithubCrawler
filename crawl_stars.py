import os
import time
import logging
from typing import List, Dict, Any
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GITHUB_ENDPOINT = "https://api.github.com/graphql"

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
    headers = {"Authorization": f"Bearer {token}"}
    transport = RequestsHTTPTransport(url=GITHUB_ENDPOINT, headers=headers)
    return Client(transport=transport, fetch_schema_from_transport=True)

def fetch_repos(client: Client, target_count: int = 100000) -> List[Dict[str, Any]]:
    repos = []
    query = "stars:>0"  
    first = 1000
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

            time.sleep(1)  # Safe rate limit

        except Exception as e:
            print(f"[FETCH ERROR] {e}")
            time.sleep(60)
            continue

    print(f"[DEBUG] Fetched {len(repos)} repositories")
    if repos:
        print(f"[SAMPLE] First repo: {repos[0]}")
    return repos

def upsert_repos_to_db(repos: List[Dict[str, Any]], db_host: str, db_port: int, db_name: str, db_user: str, db_pass: str):
    try:
        print(f"[DB] Connecting to: {db_host}:{db_port}/{db_name}")
        conn = psycopg2.connect(
            host=db_host, port=db_port, dbname=db_name, user=db_user, password=db_pass
        )
        print("[DB] Connected successfully!")
        
        cur = conn.cursor()

        data = [
            (repo["name_with_owner"], repo["stargazer_count"], "NOW()")
            for repo in repos
        ]

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
        print(f"[DB] SUCCESS: Upserted {len(data)} repos")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        raise e

if __name__ == "__main__":
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN required")

    client = get_github_client(token)
    repos = fetch_repos(client)
    upsert_repos_to_db(
        repos,
        db_host=os.getenv("POSTGRES_HOST", "localhost"),
        db_port=int(os.getenv("POSTGRES_PORT", 5432)),
        db_name=os.getenv("POSTGRES_DB", "postgres"),
        db_user=os.getenv("POSTGRES_USER", "postgres"),
        db_pass=os.getenv("POSTGRES_PASSWORD", "")
    )