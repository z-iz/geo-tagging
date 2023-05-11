import pandas as ps
import argparse
from pathlib import Path
import re
import requests
from time import sleep
import sys
import simplejson as json

# Parameters of request to Nominatim API of OSM
URL = 'https://nominatim.openstreetmap.org/search'
LOOKUP_CLASSES = ['boundary', 'place']
LOOKUP_TYPES = ['administrative', 'village']
LOOKUP_LIMIT = 3

# Tuples of column names to be saved to the resulting table and corresponding fields in the API response
OBJECT_NAME = 'Object_name', 'display_name'
LATITUDE = 'Latitude', 'lat'
LONGITUDE = 'Longitude', 'lon'
SEARCH_QUERY = 'Search_query', ''


def detect_delimiter(csv_file):
    with open(csv_file, 'r') as myCsvfile:
        header = myCsvfile.readline()
        if header.find(";") != -1:
            return ";"
        if header.find(",") != -1:
            return ","
    # default delimiter (MS Office export)
    return ";"


def split_at(s, delim, n):
    s_split = s.split(delim, n)
    if n >= len(s_split):
        return s, ''
    else:
        r = s_split[n] if n < len(s_split) else ''
        return s[:-len(r) - len(delim)], r


if __name__ == '__main__':
    # Get paths from command line arguments
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-s", "--source", help="Path to source CSV file", type=Path)
    argParser.add_argument("-r", "--result", help="Path to result CSV file", type=Path)
    argParser.add_argument("-c", "--columns", help="Columns describing location", type=Path)

    args = argParser.parse_args()

    # Convert paths to strings
    source_path = str(args.source)
    result_path = str(args.result)
    config_columns = str(args.columns)

    # Get CSV delimiter
    delimiter = detect_delimiter(source_path)

    print('********************************************************************************************')
    print("Processing file: " + source_path)

    # Read source table
    source = ps.read_csv(source_path, sep=delimiter)
    source = source.reset_index()

    # Check that source table contains columns specified
    source_column_names = source.columns.values
    config_column_names = config_columns.split(",")
    check = all(item in source_column_names for item in config_column_names) & (len(config_column_names) == 3)

    if check is False:
        raise ValueError("Incorrect number of columns specified, " +
                         "or columns specified are not present in the source file")

    # Get column names to add
    first_loc_column = config_column_names[0]
    second_loc_column = config_column_names[1]
    third_loc_column = config_column_names[2]

    # Add columns for geo data
    column_index = source.columns.get_loc(third_loc_column)
    source.insert(column_index + 1, OBJECT_NAME[0], '')
    source.insert(column_index + 2, LATITUDE[0], '')
    source.insert(column_index + 3, LONGITUDE[0], '')
    source.insert(column_index + 4, SEARCH_QUERY[0], '')

    # Iterate over rows in the source table
    for index, row in source.iterrows():
        first_loc_item = str(row[first_loc_column])
        second_loc_item = str(row[second_loc_column])
        third_loc_item = str(row[third_loc_column]) if str(row[third_loc_column]) != "nan" else ""

        # Concatenate location string, remove newlines
        location = (first_loc_item + " " + second_loc_item + " " + third_loc_item).replace('\n', "")

        # Remove expressions in brackets
        location = re.sub("[\(\[].*?[\)\]]", "", location)

        # Remove special characters and numbers
        location = re.sub('[0-9()&*.,”“’]+', '', location).strip().replace('/', ' ').replace('  ', ' ')

        # Remove spaces around dashes
        location = re.sub(r"\s?-\s?", '-', location)
        location = re.sub(r"\s?–\s?", ' ', location)

        # Replace spaces with plus for request parameter and split it to words
        location = location.replace(' ', '+')
        location_words = location.split('+')
        num_words = len(location_words)

        # Iterate over words in the search query, starting with full query and removing words from the end
        for i in range(num_words):
            sys.stdout.write('\rProcessing row {rownum} out of total {totalnum} rows. Attempt {i} out of {num_words}'
                             .format(rownum=index + 1, totalnum=len(source), i=i + 1, num_words=num_words))
            sys.stdout.flush()
            location_to_send = split_at(location, '+', num_words - i)

            payload = {'addressdetails': 1,
                       'q': location_to_send[0],
                       'format': 'json',
                       'limit': 50}

            response = requests.get(URL, params=payload)

            r_data = json.loads(response.text)

            # Iterate over the array of results in the response from OpenStreetMap
            filled = False
            for idx, r_item in enumerate(r_data):
                # We are checking the results only up to the LOOKUP_LIMIT
                if idx > LOOKUP_LIMIT - 1:
                    break

                try:
                    item_class = r_item['class']
                    item_type = r_item['type']

                    # If we found a town (should have 'administrative boundary' type and class) - save it to table and
                    # break the loop
                    if (item_class in LOOKUP_CLASSES) & (item_type in LOOKUP_TYPES):
                        source.at[index, OBJECT_NAME[0]] = r_item[OBJECT_NAME[1]]
                        source.at[index, LATITUDE[0]] = r_item[LATITUDE[1]]
                        source.at[index, LONGITUDE[0]] = r_item[LONGITUDE[1]]
                        source.at[index, SEARCH_QUERY[0]] = location_to_send[0].replace('+', ' ')
                        filled = True
                        break

                # We are continuing if the specified fields are not existing in the request
                except KeyError:
                    continue

            if filled:
                break

            sleep(0.2)

    source.to_csv(result_path, index=False, header=True, sep=delimiter)

    print('\n********************************************************************************************')
    print("Finished processing, results saved to file: " + str(result_path))
