# Sales ETL Pipeline

## Project Description

ETL pipeline for processing sales data using Apache Airflow, PySpark, PostgreSQL, and ClickHouse. 
Generates 1M sales records, processes them, and stores in databases.


## Architecture

Pipeline workflow:

```
1. Data Generation → 2. Data Cleaning → 3. PostgreSQL Load → 4. Analytics → 5. ClickHouse Transfer
```

### Steps

1. **Data Generation** - Creates 1M sales records for past year
2. **Data Cleaning** - Removes duplicates using PySpark
3. **PostgreSQL Load** - Inserts cleaned data
4. **Analytics** - Aggregations with window functions 
5. **ClickHouse Transfer** - Moves aggregated results for OLAP

### Data Schema

**Sales Table** (PostgreSQL):
- `sale_id` - Unique sale identifier
- `customer_id` - Customer identifier
- `product_id` - Product identifier
- `quantity` - Number of items purchased
- `sale_date` - Date of sale
- `sale_amount` - Total sale amount
- `region` - Customer region (North, South, East, West)

**Sales Aggregated Table** (PostgreSQL → ClickHouse):
- `region` - Region name
- `product_id` - Product identifier
- `total_sales_count` - Total number of sales
- `total_sales_amount` - Sum of all sales amounts
- `average_sale_amount` - Average sale amount
- `total_quantity` - Total quantity sold
- `rank_in_region` - Product ranking within region
- `import_date` - Date when data was imported to ClickHouse

## Tech Stack

- **Apache Airflow 2.9.3** - orchestration
- **PySpark 3.5.1** - data processing
- **PostgreSQL 13** - OLTP database
- **ClickHouse 22.8** - OLAP database  
- **Python 3.12**
- **Docker & Docker Compose**

## Project Structure

```
nova_data_task1/
├── dags/
│   └── sales_etl_pipeline.py    # main ETL DAG
├── data/                         # CSV files (generated at runtime)
├── logs/                         # airflow logs
├── plugins/                      
├── config/                       
├── clickhouse_data/              # clickhouse volume
├── docker-compose.yml            
├── Dockerfile                    # custom airflow + pyspark
├── requirements.txt              
└── README.md                     
```

## Data Sample (Срез данных)

The pipeline generates 1M sales records dynamically. Below is a sample of the data structure:

| sale_id | customer_id | product_id | quantity | sale_date  | sale_amount | region |
|---------|-------------|------------|----------|------------|-------------|--------|
| 550     | 14562       | 958        | 5        | 2025-10-06 | 1693.30     | East   |
| 669     | 15734       | 8          | 3        | 2025-08-11 | 2025.24     | South  |
| 733     | 767         | 545        | 7        | 2025-08-24 | 2178.75     | North  |
| 790     | 24464       | 293        | 3        | 2026-02-11 | 1282.62     | East   |
| 795     | 27073       | 10         | 9        | 2026-01-12 | 1189.71     | West   |
| 982     | 39800       | 238        | 5        | 2026-02-08 | 658.35      | East   |
| 1113    | 183         | 398        | 10       | 2025-05-24 | 7507.80     | North  |
| 1413    | 1194        | 440        | 6        | 2025-04-17 | 5955.60     | East   |
| 1447    | 47176       | 573        | 7        | 2025-08-23 | 6747.93     | West   |
| 1490    | 9734        | 785        | 10       | 2026-02-08 | 581.30      | East   |
| 1819    | 29469       | 241        | 5        | 2025-04-19 | 4976.75     | North  |
| 1970    | 8323        | 294        | 4        | 2025-04-24 | 1708.68     | East   |
| 2028    | 39717       | 545        | 8        | 2025-09-05 | 4929.76     | South  |
| 2088    | 24078       | 644        | 3        | 2026-02-12 | 2888.52     | South  |
| 2142    | 15036       | 399        | 6        | 2026-02-21 | 1792.92     | South  |

**Data Schema:**
- `sale_id` - unique sale identifier (1-1,000,000)
- `customer_id` - customer identifier (1-50,000)
- `product_id` - product identifier (1-1,000)
- `quantity` - items purchased (1-10)
- `sale_date` - date of sale (last 365 days)
- `sale_amount` - total amount = quantity × random_price
- `region` - customer region (North, South, East, West, Central)

CSV files are generated at runtime and excluded from git per .gitignore.

## Setup

### Requirements

- Docker Desktop
- 8GB RAM for Docker
- 10GB disk space

### Steps

1. **Clone repo**
```bash
git clone <repo-url>
cd nova_data_task1
```

2. **Build images**
```bash
docker-compose build
```

3. **Start services**
```bash
docker-compose up -d
```

4. **Wait for init** (takes 2-3 min first time)
```bash
docker-compose logs -f airflow-init
```

5. **Access Airflow UI**
- http://localhost:8080
- user: `admin` / `admin`

### Services

| Service | URL | Creds |
|---------|-----|-------|
| Airflow | http://localhost:8080 | admin / admin |
| ClickHouse | http://localhost:8124 | airflow / airflow |

## Running the Pipeline

### Manual Run

1. Go to http://localhost:8080
2. Find `sales_etl_pipeline` DAG
3. Turn it ON
4. Click Play → Trigger DAG
5. Monitor in Graph view

### Schedule

Runs **every Tuesday at 12:45 Moscow time** (09:45 UTC)

Cron: `45 9 * * 2`

### Execution Time

- ~15-25 min for 1M records
- slowest part is PostgreSQL insert

## Verification

### Check generated files
```bash
docker exec -it airflow-scheduler ls -lh /opt/airflow/data/
```

### Check PostgreSQL
```bash
docker exec -it postgres psql -U airflow -c "SELECT COUNT(*) FROM sales;"
docker exec -it postgres psql -U airflow -c "SELECT * FROM sales_aggregated LIMIT 10;"
```

### Check ClickHouse
```bash
docker exec -it clickhouse clickhouse-client --user airflow --password airflow \
    --query "SELECT COUNT(*) FROM sales_db.sales_aggregated"
```

### View logs
```bash
docker-compose logs -f airflow-scheduler
```

## Expected Results

After pipeline runs:

- **PostgreSQL `sales` table**: ~1,000,000 records (after deduplication)
- **PostgreSQL `sales_aggregated` table**: ~4,000 records (regions × products)
- **ClickHouse `sales_aggregated` table**: ~4,000 records with import_date

### ClickHouse Analytics Results

**Query 1: Total Sales by Region**
```sql
SELECT region, COUNT(*) as products, 
       SUM(total_sales_count) as total_sales, 
       ROUND(SUM(total_sales_amount), 2) as revenue 
FROM sales_db.sales_aggregated 
GROUP BY region 
ORDER BY revenue DESC;
```

**Results:**
```
Region  Products  Total Sales  Revenue
------  --------  -----------  ----------------
South   1,000     375,083      $1,053,972,397.78
East    1,000     281,158      $788,311,188.41
North   1,000     250,259      $701,329,336.60
West    1,000     93,500       $262,930,697.20
```

**Query 2: Top 5 Products per Region**
```sql
SELECT region, product_id, total_sales_count, 
       ROUND(total_sales_amount, 2) as amount, 
       rank_in_region 
FROM sales_db.sales_aggregated 
WHERE rank_in_region <= 5 
ORDER BY region, rank_in_region;
```

**Results:**
```
Region  Product  Sales Count  Amount          Rank
------  -------  -----------  --------------  ----
East    338      310          $964,524.34     1
East    647      314          $960,267.65     2
East    348      319          $953,194.42     3
East    414      314          $948,749.47     4
East    860      324          $937,478.53     5

North   578      295          $876,178.13     1
North   650      287          $873,188.77     2
North   790      290          $867,814.98     3
North   848      287          $863,571.22     4
North   647      284          $863,190.15     5

South   140      416          $1,308,702.74   1
South   41       414          $1,265,998.60   2
South   178      433          $1,259,645.74   3
South   137      426          $1,255,274.74   4
South   68       406          $1,253,801.57   5

West    320      116          $422,527.38     1
West    744      120          $410,348.87     2
West    155      123          $402,549.75     3
West    995      123          $383,140.83     4
West    195      115          $363,165.77     5
```

**Query 3: Data Import Verification**
```sql
SELECT COUNT(*) as total_records, 
       MIN(import_date) as first_import, 
       MAX(import_date) as last_import 
FROM sales_db.sales_aggregated;
```

**Results:**
```
Total Records  First Import  Last Import
-------------  ------------  -----------
4,000          2026-02-21    2026-02-21
```

## Maintenance

### Stop services
```bash
docker-compose down
```

### Clean everything (including volumes)
```bash
docker-compose down -v
rm -rf logs/* clickhouse_data/* data/*.csv
```

### Rebuild after changes
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Check service status
```bash
docker-compose ps
```

## Troubleshooting

### DAG not showing up
Check syntax:
```bash
docker exec -it airflow-scheduler python /opt/airflow/dags/sales_etl_pipeline.py
```

### PySpark Java errors
Verify Java installation:
```bash
docker exec -it airflow-scheduler java -version
```

### PostgreSQL connection issues
Check container:
```bash
docker-compose ps postgres
docker-compose logs postgres
```

### Out of memory
Increase Docker RAM to 8GB+

### CSV not found
Check mount:
```bash
docker exec -it airflow-scheduler ls -la /opt/airflow/data/
```

## Notes

### Design choices

1. **Batch inserts to PostgreSQL**
   - 1M rows at once would timeout
   - batches of 10k work well

2. **Duplicates**
   - shows realistic data quality issues
   - demonstrates PySpark dedup

3. **PostgreSQL + ClickHouse**
   - PostgreSQL for OLTP
   - ClickHouse for OLAP, fast analytics

4. **CSV not in git**
   - files generated at runtime
   - 1M records too big for repo

### Performance tweaks

- Spark coalesced writes
- Batch inserts (10k per batch)
- Pandas for ClickHouse bulk insert
- Window functions in Spark SQL

## Dependencies

See [requirements.txt](requirements.txt):

- pyspark==3.5.1
- clickhouse-connect==0.7.17
- psycopg2-binary
- pandas
- sqlalchemy

## Project Checklist

- Proper repo structure with README and Dockerfile
- Complete pipeline in single DAG
- CSV generated at runtime (not in git)
- 1M realistic records
- Deduplication working
- Window functions implemented
- Data in both databases

---

Task #10 - Sales ETL Pipeline
