#!/usr/bin/env python
import fileinput
import csv
import sys
import os
import re
from signal import signal, SIGPIPE, SIG_DFL

# Handle broken pipes gracefully
signal(SIGPIPE, SIG_DFL)

# Allow large content in the dump
csv.field_size_limit(sys.maxsize)

class TableData:
    def __init__(self, name):
        self.name = name
        self.headers = []
        self.output_file = None
        self.writer = None

def get_table_name(line):
    """
    Extracts table name from CREATE TABLE or INSERT INTO statement
    """
    match = re.search(r'(?:CREATE TABLE|INSERT INTO) [`"]?([^`"\s(]+)', line)
    return match.group(1) if match else None

def get_column_names(line):
    """
    Extracts column names from CREATE TABLE statement
    """
    # Remove comments and normalize whitespace
    line = re.sub(r'/\*.*?\*/', '', line)
    line = re.sub(r'--.*$', '', line)
    
    # Extract content between parentheses
    match = re.search(r'\((.*)\)', line, re.DOTALL)
    if not match:
        return []
    
    content = match.group(1)
    columns = []
    
    # Split by comma but ignore commas within parentheses
    parts = []
    paren_level = 0
    current = []
    
    for char in content:
        if char == '(':
            paren_level += 1
        elif char == ')':
            paren_level -= 1
        elif char == ',' and paren_level == 0:
            parts.append(''.join(current))
            current = []
            continue
        current.append(char)
    
    if current:
        parts.append(''.join(current))
    
    # Extract column names
    for part in parts:
        # Get first word, removing backticks if present
        column = part.strip().split()[0].strip('`"')
        if column and not any(keyword in part.upper() for keyword in ['PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'INDEX', 'KEY']):
            columns.append(column)
    
    return columns

def is_create_table(line):
    """
    Returns true if the line begins a CREATE TABLE statement.
    """
    return line.strip().upper().startswith('CREATE TABLE')

def is_insert(line):
    """
    Returns true if the line begins a SQL insert statement.
    """
    return line.strip().upper().startswith('INSERT INTO')

def get_values(line):
    """
    Returns the portion of an INSERT statement containing values
    """
    partition = line.partition(' VALUES ')
    if len(partition) != 3:
        return None
    return partition[2]

def values_sanity_check(values):
    """
    Ensures that values from the INSERT statement meet basic checks.
    """
    if not values:
        return False
    if not values.strip().startswith('('):
        return False
    return True

def parse_values(values, writer):
    """
    Given a CSV writer and the raw values from a MySQL INSERT
    statement, write the equivalent CSV to the file
    """
    latest_row = []
    
    # Handle multi-line INSERT statements
    values = values.strip()
    
    reader = csv.reader([values], delimiter=',',
                       doublequote=False,
                       escapechar='\\',
                       quotechar="'",
                       strict=True
    )
    
    for reader_row in reader:
        for column in reader_row:
            # Skip empty columns and NULL values
            if len(column) == 0 or column == 'NULL':
                latest_row.append('')
                continue
                
            # Handle opening parentheses
            if column[0] == "(":
                if len(latest_row) > 0 and latest_row[-1][-1] == ")":
                    latest_row[-1] = latest_row[-1][:-1]
                    writer.writerow(latest_row)
                    latest_row = []
                if len(latest_row) == 0:
                    column = column[1:]
                    
            # Handle closing parentheses and semicolons
            if column.endswith(');') or column.endswith('),'):
                column = column.rstrip(');,')
                latest_row.append(column)
                writer.writerow(latest_row)
                latest_row = []
                continue
                
            latest_row.append(column)
            
        # Handle any remaining rows
        if latest_row:
            if latest_row[-1].endswith(')'):
                latest_row[-1] = latest_row[-1][:-1]
            writer.writerow(latest_row)
            latest_row = []

def main():
    """
    Parse arguments and start the program
    """
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: python script.py <dump_file>\n")
        sys.exit(1)
        
    # Create output directory
    output_dir = "csv_output"
    os.makedirs(output_dir, exist_ok=True)
    
    tables = {}
    current_table = None
    current_insert = ''
    create_statement = ''
    
    try:
        with fileinput.input(files=(sys.argv[1],)) as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('--') or line.startswith('/*'):
                    continue
                
                # Handle CREATE TABLE statements
                if is_create_table(line):
                    create_statement = line
                    continue
                elif create_statement:
                    create_statement += ' ' + line
                    if line.endswith(';'):
                        table_name = get_table_name(create_statement)
                        if table_name:
                            headers = get_column_names(create_statement)
                            if headers:
                                tables[table_name] = TableData(table_name)
                                tables[table_name].headers = headers
                                # Create new CSV file with headers
                                output_path = os.path.join(output_dir, f"{table_name}.csv")
                                tables[table_name].output_file = open(output_path, 'w', newline='')
                                tables[table_name].writer = csv.writer(tables[table_name].output_file)
                                tables[table_name].writer.writerow(headers)
                        create_statement = ''
                
                # Handle INSERT statements
                if is_insert(line):
                    table_name = get_table_name(line)
                    if table_name in tables:
                        current_table = tables[table_name]
                        current_insert = line
                elif current_insert:
                    current_insert += ' ' + line
                
                # Process complete INSERT statements
                if current_insert and ';' in line:
                    values = get_values(current_insert)
                    if values and values_sanity_check(values) and current_table:
                        parse_values(values, current_table.writer)
                    current_insert = ''
                    
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)
    finally:
        # Close all open files
        for table in tables.values():
            if table.output_file:
                table.output_file.close()

if __name__ == "__main__":
    main()
