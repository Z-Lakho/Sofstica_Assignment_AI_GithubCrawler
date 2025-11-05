## GitHub Stars Crawler

This project is a GitHub Stars Crawler that uses GitHub’s GraphQL API to fetch repositories and their star counts, then stores the data into a PostgreSQL database.

It was developed as part of a Software Engineer Take-Home Assignment.

# What This Project Does

The crawler connects to GitHub’s GraphQL endpoint, fetches repositories (by default targeting those with at least one star ⭐), and saves their name_with_owner and stargazer_count into a relational database.

The crawler supports upsert operations, meaning:

If a repository already exists, only its star count and timestamp are updated.

If it’s new, it’s inserted.

Finally, the data can be dumped to a CSV file for easy sharing or further analysis.

# Why Only 1000 Rows?

Although the assignment mentioned 100,000 repositories, this implementation currently handles only 1,000 rows because of time constraints and GitHub API rate limits.

The logic, however, is scalable — by adjusting the target_count parameter in crawl_stars.py, the same code can handle much larger datasets.

# Architecture Overview

This project follows clean and modular design:

crawl_stars.py → Handles fetching data from GitHub and inserting/updating records in Postgres.

dump_db.py → Exports the stored data from Postgres into a CSV.

crawl.yml → GitHub Actions workflow that automates setup, crawl, and dump steps.

Core design principles used:

Separation of concerns: Crawling, database management, and CI/CD are separate modules.

Error handling: Retry logic and exception management to handle API failures gracefully.

Immutability: Once fetched, data is not mutated in memory beyond upsert preparation.

# Database Schema

The repositories table includes:

Column	Type	Description
name_with_owner	TEXT (PK)	Unique repo name (e.g., facebook/react)
stargazer_count	INTEGER	Number of stars
updated_at	TIMESTAMP	Last time the repo data was updated

 ## Answers to Assignment Questions
1. What would you do differently for 500 million repositories?

Handling 500M repos would require:

Distributed Crawling: Use multiple workers or services to parallelize API calls while respecting rate limits.

Batch Processing: Introduce message queues (e.g., Kafka or RabbitMQ) to distribute tasks.

Asynchronous Requests: Replace synchronous GraphQL calls with async fetching.

Sharded Database Design: Partition tables across multiple database nodes for scalability.

Cloud Storage Integration: Store raw data in object storage (S3, GCS) before inserting into DB.

Incremental Updates: Use updatedAt field from GitHub API to only fetch deltas daily.

2️. How will the schema evolve for more metadata (issues, PRs, comments, etc.)?

To handle more metadata efficiently:

Introduce related tables (e.g., issues, pull_requests, comments, reviews).

Maintain foreign keys linking each to a repository.

Store timestamps and counts, so new comments or reviews trigger only row-level updates, not full rewrites.

Use partitioned tables for large data volumes.

Add indexing on frequently queried fields like repo_id, issue_id.

This ensures efficient incremental updates with minimal row changes.

3️. Why is duration important?

GitHub crawling should be as fast as possible without violating rate limits.
The script uses:

Batched requests of 100 repos per query.

Retry and sleep mechanism (1-second delay).

Efficient upsert operation instead of individual inserts.

4️. What are the software engineering practices applied?

Clean architecture

Logging for debugging and performance tracking

Retry mechanisms

Error resilience

Modular code

Environment variables for flexibility

CI/CD integration with GitHub Actions

## How to Run Locally
=> Prerequisites

Python 3.9+

PostgreSQL running locally

A valid GitHub Personal Access Token (with public repo access)

=> Steps

Clone the repository:

git clone <your_repo_url>
cd <repo_name>

Install dependencies:

pip install gql psycopg2 requests


Run the crawler (default: 1000 repos):

python crawl_stars.py


Export data to CSV:

python dump_db.py


The file repos.csv will be created in the project directory.

## GitHub Actions Workflow (crawl.yml)

The workflow automates:

Setting up Python and Postgres containers.

Installing dependencies.

Running the crawler to fetch and insert repos.

Exporting data as an artifact.

It uses the default GitHub Token (no secrets required).
