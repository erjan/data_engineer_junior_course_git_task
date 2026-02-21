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
├── data/                         # CSV files
├── logs/                         # airflow logs
├── plugins/                      
├── config/                       
├── clickhouse_data/              # clickhouse volume
├── docker-compose.yml            
├── Dockerfile                    # custom airflow + pyspark
├── requirements.txt              
└── README.md                     
```

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

### Sample Analytics Output

```
Region | Product ID | Total Sales | Total Amount | Avg Amount | Rank
-------|------------|-------------|--------------|------------|-----
North  | 542        | 1,234       | 123,456.78   | 100.05     | 1
North  | 789        | 1,100       | 98,765.43    | 89.79      | 2
South  | 234        | 1,567       | 145,678.90   | 92.96      | 1
...
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
