# Graduate Lab: Building a "DuckLake" with NOAA Weather Data

Note: This is the second of five graduate labs.

**Estimated time:** 30-45 minutes

---

## 1. Introduction

A **DuckLake** is a modern data lakehouse pattern where **DuckDB** acts as the compute engine and metadata catalog, while **Amazon S3** provides the storage layer. This architecture allows for high-performance analytics without the overhead of a managed database server.

Be aware that alternate database engines such as PostgreSQL, MySQL hosted locally or remotely would be more appropriate for a production-grade lakehouse. DuckDB using a local file keeps the database requirement simple for this lab.

### Learning Objectives

* Configure DuckDB for S3 interoperability.
* Implement a **Medallion Architecture** (Bronze/Silver layers).
* Manage **Data Versioning** via S3 prefixes and DuckDB views.
* Utilize **GLOB patterns** and **Hive Partitioning** for scalable discovery.

---

## 2. Environment Setup

Create a new S3 bucket for this lab using the AWS CLI:

```
aws s3 mb s3://YOUR-BUCKET/
```

Be sure to specify your bucket name in the following code snippets.

Install the [**DuckDB CLI**](https://duckdb.org/install/) locally if needed. Launch the DuckDB CLI and create a local database file. This file will store your schemas, view definitions, and file pointers (the **Metadata Store**).

```bash
duckdb weather_lake.duckdb
```

Within the DuckDB prompt, initialize your cloud extensions and credentials:

```sql
-- Install and load cloud extensions
INSTALL httpfs;
INSTALL aws;
LOAD httpfs;
LOAD aws;

-- Automatically detect local AWS credentials (~/.aws/credentials)
CALL load_aws_credentials();
```

**NOTE:** These install/load commands can be put into a `~/.duckdbrc` file that loads automatically with DuckDB.

---

## 3. The Bronze Layer: Multi-City Ingestion

We will fetch 2023 weather data for Chicago, New York, and Los Angeles and "land" it in your private S3 bucket.

```sql
-- Ingest three cities into one 'raw' Parquet file on S3 (Bronze v1)
COPY (
    SELECT *, 'Chicago' as city FROM 'https://noaa-gsod-pds.s3.amazonaws.com/2023/72530094846.csv'
    UNION ALL
    SELECT *, 'New York' as city FROM 'https://noaa-gsod-pds.s3.amazonaws.com/2023/74486094789.csv'
    UNION ALL
    SELECT *, 'Los Angeles' as city FROM 'https://noaa-gsod-pds.s3.amazonaws.com/2023/72295023174.csv'
) TO 's3://YOUR-BUCKET/bronze/v1/weather_raw.parquet' (FORMAT PARQUET);
```

---

## 4. The Silver Layer: Refinement & Versioning

We will manage two versions of our data to see how the metadata store tracks changes.

### Version 1: The "As-Is" View

Create a view that maps the raw S3 data without transformations.

```sql
CREATE SCHEMA silver;

CREATE VIEW silver.weather_v1 AS 
SELECT city, date, temp AS temp_f, wdsp AS wind_knots
FROM 's3://YOUR-BUCKET/bronze/v1/weather_raw.parquet';
```

### Version 2: The Refined Dataset

We will now clean the data (convert to Celsius and handle NOAA's `99.9` null placeholders) and write a new physical version to S3.

```sql
-- Write refined data to a new S3 prefix (v2)
COPY (
    SELECT 
        city,
        date::DATE as obs_date,
        (temp - 32) * 5/9 AS temp_c,
        CASE WHEN wdsp = 999.9 THEN NULL ELSE wdsp END AS wind_speed_ms
    FROM 's3://YOUR-BUCKET/bronze/v1/weather_raw.parquet'
    WHERE temp != 99.9
) TO 's3://YOUR-BUCKET/silver/v2/weather_refined.parquet' (FORMAT PARQUET);

-- Register V2 in the local metadata catalog
CREATE VIEW silver.weather_v2 AS 
SELECT * FROM 's3://YOUR-BUCKET/silver/v2/weather_refined.parquet';
```

---

## 5. Scaling with GLOB Patterns & Hive Partitioning

We will now export the data in a **Hive-partitioned** format and use **GLOB patterns** to read the entire lake.

### Step A: Partitioned Export

```sql
COPY silver.weather_v2 
TO 's3://YOUR-BUCKET/silver/v3_partitioned/' 
(FORMAT PARQUET, PARTITION_BY (city));
```

### Step B: Discovery via GLOB

DuckDB uses the `**` pattern to recursively scan folders. It will automatically detect the `city` column from the folder names (Hive Discovery).

```sql
-- Query the entire lake using a GLOB pattern
SELECT city, ROUND(AVG(temp_c), 2) as avg_temp
FROM 's3://YOUR-BUCKET/silver/v3_partitioned/**/*.parquet'
GROUP BY city;
```

---

## 6. Knowledge Check

1. **Separation of Concerns:** Where is the "Metadata" stored, and where is the "Data" stored? Why is this separation beneficial?
2. **Predicate Pushdown:** If you run a query filtering for `city = 'Chicago'`, does DuckDB download the data for New York?
3. **Versioning Strategy:** How does the local `.duckdb` file help a Data Analyst switch between data versions?
4. **The Role of Parquet:** Why convert CSV files to Parquet for the Silver layer?
5. **Globbing:** What is the difference between `*.parquet` and `**/*.parquet`?

---

## 7. Cleanup 

```bash
aws s3 rm s3://YOUR-BUCKET/ --recursive
aws s3 rb s3://YOUR-BUCKET/
```

---

## Answer Key
1. **Separation:** Metadata is in the local `weather_lake.duckdb` file; Data is in S3. This is beneficial because compute/metadata are "ephemeral" and cheap, while storage is centralized, durable, and scales infinitely.
2. **Pushdown:** No. Because of Hive Partitioning, DuckDB performs "Partition Pruning"—it only hits the S3 prefix for Chicago and ignores the other folders entirely.
3. **Versioning:** The analyst can maintain multiple Views (e.g., `weather_v1`, `weather_v2`) in the same catalog pointing to different S3 paths, allowing for instant "A/B" testing of logic.
4. **Parquet:** Parquet is a columnar data format, optimized for analytics. DuckDB can use "Range Requests" to download only the columns needed (e.g., just `temp`), whereas CSV requires downloading the whole file to parse it.
5. **Globbing:** `*.parquet` looks only in the top-level directory. `**/*.parquet` is recursive, searching through all subdirectories (essential for Hive-partitioned structures).
---
