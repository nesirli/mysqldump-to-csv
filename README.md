# MySQL Dump to CSV Converter

A Python script that converts MySQL dump files into CSV format. The script processes MySQL dump files containing INSERT statements and creates separate CSV files for each table found in the dump.

## Features

- Converts MySQL dump files to CSV format
- Creates separate CSV files for each table
- Handles multiple INSERT statements per table

## Requirements

- Python 3.x
- No additional packages required (uses only Python standard library)

## Installation

Clone this repository:

```bash
git clone https://github.com/nesirli/mysqldump-to-csv.git
cd mysql-dump-to-csv
```

Make the script executable:

```bash
chmod +x mysqldump_to_csv.py
```

## Usage

```bash
python mysqldump_to_csv.py <input_dump_file>
```

### Arguments:

- `input_dump_file`: Path to the MySQL dump file


## Input Format

The script expects a MySQL dump file containing INSERT statements in the following format:

```sql
INSERT INTO `table_name` VALUES ('value1', 'value2', ...);
-- or
INSERT INTO `table_name` (column1, column2, ...) VALUES ('value1', 'value2', ...);
```

## Output

- Creates one CSV file per table found in the dump file
- Files are named `<table_name>.csv`
- If column names are present in the INSERT statement, they are used as headers in the CSV
- NULL values are converted to empty strings in the CSV

## Limitations

- Only processes INSERT statements
- Assumes UTF-8 encoding for input and output files
