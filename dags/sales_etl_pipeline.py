"""
Sales ETL Pipeline
==================
Generates 1M sales records, cleans them with PySpark, 
loads to PostgreSQL, runs analytics, transfers to ClickHouse

Schedule: Tuesdays 12:45 Moscow time
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as _sum, avg, count, row_number, to_date, current_date
from pyspark.sql.window import Window
import random
from clickhouse_connect import get_client
import psycopg2
from psycopg2.extras import execute_batch
import pandas as pd


# paths and stuff
DATA_PATH = "/opt/airflow/data/sales_data.csv"
CLEAN_DATA_PATH = "/opt/airflow/data/sales_data_clean.csv"

# db config
PG_HOST = "postgres"
PG_PORT = 5432
PG_DB = "airflow"
PG_USER = "airflow"
PG_PASSWORD = "airflow"

# ClickHouse config
CH_HOST = "clickhouse"
CH_USER = "airflow"
CH_PASSWORD = "airflow"
CH_DB = "sales_db"


def generate_sales_data():
    """
    Task 1: Generate 1 million realistic sales records for the last year
    """
    print("Starting sales data generation...")
    
    spark = SparkSession.builder \
        .appName("SalesDataGeneration") \
        .config("spark.master", "local[*]") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()
    
    from pyspark.sql.functions import expr, lit
    from datetime import date
    
    # Generate 1 million records
    num_records = 1_000_000
    
    # Create DataFrame with sequential IDs
    df = spark.range(0, num_records)
    
    # Add columns
    df = df.select(
        (col("id") + 1).alias("sale_id"),
        (expr("cast(rand() * 50000 as int) + 1")).alias("customer_id"),
        (expr("cast(rand() * 1000 as int) + 1")).alias("product_id"),
        (expr("cast(rand() * 10 as int) + 1")).alias("quantity"),
        expr("date_sub(current_date(), cast(rand() * 365 as int))").alias("sale_date"),
        (expr("cast(rand() * 1000 as decimal(10,2)) + 10")).alias("price_per_unit")
    )
    
    # calc sale_amount
    df = df.withColumn("sale_amount", col("quantity") * col("price_per_unit"))
    
    # Add region with distribution
    df = df.withColumn(
        "region",
        expr("""
            CASE 
                WHEN rand() < 0.25 THEN 'North'
                WHEN rand() < 0.50 THEN 'South'
                WHEN rand() < 0.75 THEN 'East'
                ELSE 'West'
            END
        """)
    )
    
    # Select final columns
    df = df.select(
        "sale_id",
        "customer_id",
        "product_id",
        "quantity",
        "sale_date",
        "sale_amount",
        "region"
    )
    
    # Add some duplicates (1%)
    sample_df = df.sample(fraction=0.01, seed=42)
    df_with_duplicates = df.union(sample_df)
    
    # print("Debug: count before save", df_with_duplicates.count())  # keep for debugging
    
    # Save to CSV
    df_with_duplicates.coalesce(1).write \
        .mode("overwrite") \
        .option("header", "true") \
        .csv("/tmp/sales_temp")
    
    # Move CSV to correct location
    import os
    import shutil
    temp_files = [f for f in os.listdir("/tmp/sales_temp") if f.endswith(".csv")]
    if temp_files:
        shutil.move(f"/tmp/sales_temp/{temp_files[0]}", DATA_PATH)
        shutil.rmtree("/tmp/sales_temp")
    
    record_cnt = df_with_duplicates.count()
    print(f"Generated {record_cnt} sales records (including duplicates)")
    print(f"Data saved to {DATA_PATH}")
    
    spark.stop()


def clean_and_transform_data():
    # remove duplicates and fix data types
    print("Starting data cleaning and transformation...")
    
    # init spark
    spark = SparkSession.builder \
        .appName("SalesDataCleaning") \
        .config("spark.master", "local[*]") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()
    
    # Load data
    df = spark.read.option("header", "true").csv(DATA_PATH)
    
    initial_count = df.count()
    print(f"Initial record count: {initial_count}")
    
    # convert column types to correct ones
    df = df.withColumn("sale_id", col("sale_id").cast("int")) \
           .withColumn("customer_id", col("customer_id").cast("int")) \
           .withColumn("product_id", col("product_id").cast("int")) \
           .withColumn("quantity", col("quantity").cast("int")) \
           .withColumn("sale_date", to_date(col("sale_date"))) \
           .withColumn("sale_amount", col("sale_amount").cast("decimal(10,2)"))
    
    # Remove duplicates based on all columns
    df_clean = df.dropDuplicates()
    
    clean_count = df_clean.count()
    print(f"Records after deduplication: {clean_count}")
    duplicates_removed = df.count() - clean_count
    print(f"Removed {duplicates_removed} duplicate records")
    
    # save cleaned data
    df_clean.coalesce(1).write \
        .mode("overwrite") \
        .option("header", "true") \
        .csv("/tmp/sales_clean_temp")
    
    # Move the cleaned CSV
    import os
    import shutil
    temp_files = [f for f in os.listdir("/tmp/sales_clean_temp") if f.endswith(".csv")]
    if temp_files:
        clean_path = "/opt/airflow/data/sales_data_clean.csv"
        shutil.move(f"/tmp/sales_clean_temp/{temp_files[0]}", clean_path)
        shutil.rmtree("/tmp/sales_clean_temp")
        print(f"Cleaned data saved to {clean_path}")
    
    # print sample
    print("\nSample of cleaned data:")
    df_clean.show(10, truncate=False)
    
    spark.stop()


def load_to_postgresql():
    # load cleaned data to postgres
    # TODO: maybe add partitioning if dataset gets bigger
    print("Loading data to PostgreSQL...")
    
    spark = SparkSession.builder \
        .appName("LoadToPostgreSQL") \
        .config("spark.master", "local[*]") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()
    
    # Load cleaned data
    clean_path = "/opt/airflow/data/sales_data_clean.csv"
    df = spark.read.option("header", "true").csv(clean_path)
    
    # Cast to proper types
    df = df.withColumn("sale_id", col("sale_id").cast("int")) \
           .withColumn("customer_id", col("customer_id").cast("int")) \
           .withColumn("product_id", col("product_id").cast("int")) \
           .withColumn("quantity", col("quantity").cast("int")) \
           .withColumn("sale_date", to_date(col("sale_date"))) \
           .withColumn("sale_amount", col("sale_amount").cast("decimal(10,2)"))
    
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )
    cursor = conn.cursor()
    
    # Create sales table
    cursor.execute("""
        DROP TABLE IF EXISTS sales CASCADE;
    """)
    
    cursor.execute("""
        CREATE TABLE sales (
            sale_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            sale_date DATE NOT NULL,
            sale_amount NUMERIC(10,2) NOT NULL,
            region VARCHAR(50) NOT NULL
        );
    """)
    
    print("Sales table created in PostgreSQL")
    
    conn.commit()
    
    # Convert to Pandas and insert in batches
    pdf = df.toPandas()
    
    # Insert data in batches
    batch_size = 10000
    total_rows = len(pdf)
    
    insert_query = """
        INSERT INTO sales (sale_id, customer_id, product_id, quantity, sale_date, sale_amount, region)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    for i in range(0, total_rows, batch_size):
        batch = pdf.iloc[i:i+batch_size]
        data = [tuple(x) for x in batch.values]
        execute_batch(cursor, insert_query, data)
        conn.commit()
        batch_num = i//batch_size + 1
        total_batches = (total_rows//batch_size) + 1
        if batch_num % 10 == 0:  # print every 10th batch to avoid log spam
            print(f"Inserted batch {batch_num}/{total_batches}")
    
    # verify count
    cursor.execute("SELECT COUNT(*) FROM sales")
    count = cursor.fetchone()[0]
    print(f"Successfully loaded {count} records to PostgreSQL")
    
    cursor.close()
    conn.close()
    spark.stop()


def perform_analytics():
    # analytics with window functions
    # calculate total sales, avg amounts per region/product
    print("Performing analytics with window functions...")
    
    spark = SparkSession.builder \
        .appName("SalesAnalytics") \
        .config("spark.master", "local[*]") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()
    
    # Read data from PostgreSQL using Spark
    jdbc_url = f"jdbc:postgresql://{PG_HOST}:{PG_PORT}/{PG_DB}"
    
    df = spark.read \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", "sales") \
        .option("user", PG_USER) \
        .option("password", PG_PASSWORD) \
        .option("driver", "org.postgresql.Driver") \
        .load()
    
    row_count = df.count()
    print(f"Loaded {row_count} records from PostgreSQL")
    
    # Perform aggregations
    agg_df = df.groupBy("region", "product_id") \
        .agg(
            count("sale_id").alias("total_sales_count"),
            _sum("sale_amount").alias("total_sales_amount"),
            avg("sale_amount").alias("average_sale_amount"),
            _sum("quantity").alias("total_quantity")
        )
    
    # Add ranking using window function
    window_spec = Window.partitionBy("region").orderBy(col("total_sales_amount").desc())
    agg_df = agg_df.withColumn("rank_in_region", row_number().over(window_spec))
    
    # Round decimal values
    agg_df = agg_df.withColumn("total_sales_amount", col("total_sales_amount").cast("decimal(15,2)")) \
                   .withColumn("average_sale_amount", col("average_sale_amount").cast("decimal(10,2)"))
    
    print("\nAnalytics Results (Top 5 per region):")
    agg_df.filter(col("rank_in_region") <= 5).orderBy("region", "rank_in_region").show(20, truncate=False)
    
    # Save aggregated data to PostgreSQL
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )
    cursor = conn.cursor()
    
    # Create aggregated sales table
    cursor.execute("""
        DROP TABLE IF EXISTS sales_aggregated CASCADE;
    """)
    
    cursor.execute("""
        CREATE TABLE sales_aggregated (
            region VARCHAR(50),
            product_id INTEGER,
            total_sales_count BIGINT,
            total_sales_amount NUMERIC(15,2),
            average_sale_amount NUMERIC(10,2),
            total_quantity BIGINT,
            rank_in_region INTEGER,
            PRIMARY KEY (region, product_id)
        );
    """)
    
    conn.commit()
    print("Sales aggregated table created")
    
    # Convert to Pandas and insert
    pdf = agg_df.toPandas()
    
    insert_query = """
        INSERT INTO sales_aggregated 
        (region, product_id, total_sales_count, total_sales_amount, 
         average_sale_amount, total_quantity, rank_in_region)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    data = [tuple(x) for x in pdf.values]
    execute_batch(cursor, insert_query, data)
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM sales_aggregated")
    record_count = cursor.fetchone()[0]
    print(f"Successfully saved {record_count} aggregated records to PostgreSQL")
    
    cursor.close()
    conn.close()
    spark.stop()


def transfer_to_clickhouse():
    # transfer aggregated results to clickhouse
    print("Transferring aggregated data to ClickHouse...")
    
    # Read from PostgreSQL
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )
    
    query = "SELECT * FROM sales_aggregated"
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"Loaded {len(df)} aggregated records from PostgreSQL")
    
    # Add import date
    df['import_date'] = pd.Timestamp.now().date()
    
    # Connect to ClickHouse
    client = get_client(
        host=CH_HOST,
        username=CH_USER,
        password=CH_PASSWORD
    )
    
    # Create database if not exists
    client.command(f"CREATE DATABASE IF NOT EXISTS {CH_DB}")
    
    # Drop table if exists to avoid permission issues
    try:
        client.command(f"DROP TABLE IF EXISTS {CH_DB}.sales_aggregated")
    except:
        pass
    
    # Create table in ClickHouse with simpler engine
    client.command(f"""
        CREATE TABLE {CH_DB}.sales_aggregated (
            region String,
            product_id Int32,
            total_sales_count Int64,
            total_sales_amount Decimal(15,2),
            average_sale_amount Decimal(10,2),
            total_quantity Int64,
            rank_in_region Int32,
            import_date Date
        ) ENGINE = Log
    """)
    
    print("ClickHouse table created")
    
    # Insert data
    client.insert_df(f"{CH_DB}.sales_aggregated", df)
    
    # verify transfer
    result = client.command(f"SELECT COUNT(*) FROM {CH_DB}.sales_aggregated")
    print(f"Successfully transferred {result} records to ClickHouse")
    
    # show sample for verification
    sample = client.query(f"""
        SELECT * FROM {CH_DB}.sales_aggregated 
        ORDER BY region, total_sales_amount DESC 
        LIMIT 10
    """)
    print("\nSample data in ClickHouse:")
    print(sample.result_rows)
    
    client.close()


# DAG Definition
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
with DAG(
    dag_id='sales_etl_pipeline',
    default_args=default_args,
    description='Sales ETL: Generate -> Clean -> PostgreSQL -> Analytics -> ClickHouse',
    schedule_interval='45 9 * * 2',  # Tuesdays 09:45 UTC = 12:45 Moscow
    catchup=False,
    tags=['sales', 'etl', 'pyspark'],
) as dag:
    
    # tasks
    task_generate = PythonOperator(
        task_id='generate_sales_data',
        python_callable=generate_sales_data,
    )
    
    task_clean = PythonOperator(
        task_id='clean_transform_data',
        python_callable=clean_and_transform_data,
    )
    
    task_load_pg = PythonOperator(
        task_id='load_to_postgresql',
        python_callable=load_to_postgresql,
    )
    
    task_analytics = PythonOperator(
        task_id='perform_analytics',
        python_callable=perform_analytics,
    )
    
    task_transfer_ch = PythonOperator(
        task_id='transfer_to_clickhouse',
        python_callable=transfer_to_clickhouse,
    )
    
    # pipeline flow
    task_generate >> task_clean >> task_load_pg >> task_analytics >> task_transfer_ch
