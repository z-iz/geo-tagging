# geo-tagging
Python script to lookup and add geolocation data to tables having address information about geographical objects.

## Overview
This script uses OpenStreetMap [Nominatim API](https://nominatim.org) to search for geographical objects based on their
location info stored in one or more columns of the source table.

The GPS coordinates and other data is then added to the source table.

## How to install
The script runs with Python 3.8 and above and uses the following dependencies:
* [Pandas](https://pandas.pydata.org)

Install the above dependencies first, then download the [script file](main.py).

## How to use
Run the script with the following command-line arguments:

```
python3 main.py \
-s <path to source CSV file> \
-r <path to output CSV file> \
-c <comma separated list of columns with location info>
```

Example:
```
python3 main.py -s ./source/Output_Table_D1.csv -r ./result/result.csv -c "Country,Locality,Plant_name"
```

### Source CSV file and location columns
In the source CSV file, address or other location info about the objects should be stored in one or several columns.
Comma-separated list of these columns' names should be passed to the script as an argument with `-c` flag.
The script expects that exactly 3 location column names will be passed. This was hard-coded for simplicity, but hopefully will be refactored later.

### Configuration

To configure which objects are searched for, adjust the following section in the script header:
```
LOOKUP_CLASSES = ['boundary', 'place']
LOOKUP_TYPES = ['administrative', 'village']
LOOKUP_LIMIT = 3
```
`LOOKUP_CLASSES` enumerates the classes of objects to look for (see Nominatim API documentation for details)
`LOOKUP_TYPES` enumerates the types of objects to look for (see Nominatim API documentation for details)
`LOOKUP_LIMIT` sets the maximum number of results in the response to be processed

The following section in the script allows to configure the fields in the API response to be saved to the resulting table
and the respective column names:
```
OBJECT_NAME = 'Object_name', 'display_name'
LATITUDE = 'Latitude', 'lat'
LONGITUDE = 'Longitude', 'lon'
SEARCH_QUERY = 'Search_query', ''
```
_NB: Script needs to be edited accordingly if the number of the configured fields is changed_

### Processing
For each of the rows in the source file, the script:
* Generates the search query by concatenating the contents of location columns and cleaning the result from special symbols
* Attempts to query Nominatim API with the search query.
* If the response has the object of specified class and type within the specified limit, then the script adds the respective data to resulting table
* Else, the search query is trimmed by 1 word and the new request is sent

Processing stops when there are no words left in the request.
A sleep time of 0,2 s is used between API requests to Nominatim to ratelimit the load.

### Result

Resulting CSV file will have the columns with location data obtained for the most narrow query, along with the query itself in the "Search_query" column.
