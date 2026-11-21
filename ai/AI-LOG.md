# AI log

> **What goes here:** one table row for each substantial piece of AI-assisted work,
> newest first, and one short paragraph for each AI extension. Save prompts in
> `ai/prompts/` and link them. A check counts only if its evidence is linked; check
> numbers refer to the
> [AI verification checklist](https://stat.cmu.edu/~sgallagh/courses/mads-fall-2026/computing-36614/ai-verification-checklist.html).
> Receivers add their rows here too. Replace the example.

## Entries

| Date | Phase | Piece | Tool | Prompt | Kept, changed, or rejected | Checks and evidence |
|---|---|---|---|---|---|---|
| 2026-11-10 | building | Refine table schema requirements like types, keys, and constraints | Gemini | [prompt](prompts/2026-11-10-schema.txt) | Kept all fundamental table designs and column names; changed `INT` ids to `BIGINT` to handle overflow, changed `FLOAT` type of currencies to `NUMERIC`, standardized timestamp columns to `TIMESTAMPZ` type, added CHECK constraints using regex and range | 1: Verified all 9 tables were created (`sql/tests/t00-table-schemas.sql`) |
| 2026-11-10 | building | Review NOAA Storm Events ingestion for potential SQL injection vulnerabilities | ChatGPT | [prompt](prompts/2026-11-10-storm-etl-sql-security.txt) | Kept the use of PostgreSQL COPY for bulk data ingestion and reviewed how separating external data values from executable SQL prevents SQL injection | Reviewed the data-loading implementation; an adversarial input test is needed for stronger verification |
| 2026-11-10 | building | Develop an efficient refresh process for NOAA Storm Events data | ChatGPT | [prompt](prompts/2026-11-10-storm-events-refresh.txt) | Used a staging table and bulk COPY operations to load incoming records before merging them into the permanent table; used event identifiers to prevent duplicate records and account for revisions to existing events | Implementation in [refresh_storms.py](../src/refresh_storms.py); verify by rerunning the refresh and comparing stored records |
| 2026-11-10 | building | Develop the initial ETL process for NOAA Storm Events bulk CSV files | ChatGPT | [prompt](prompts/2026-11-10-storm-events-etl.txt) | Used pandas to read compressed CSV files directly rather than manually decompressing them; refined the data selection, cleaning, and PostgreSQL loading procedures to match the project schema | Compare source records against loaded PostgreSQL records using the storm events validation tests |
| 2026-11-14 | building | Write script for connecting to and loading NWS data from API | Gemini | [prompt](prompts/2026-11-14-nws-table.txt) | Kept 3-part underlying structure given in starter code; changed API to load from NWS observations and alerts (both in one file), updated which stations to pull | 1: Ran the script twice and verified run 1 stated "had 0 rows and now has 2500" for observations and run 2 stated "had 2500 rows and now has 2500 rows"|
| 2026-11-14 | building | Write script for loading HURDAT2 CSV data | Gemini | [prompt](prompts/2026-11-14-hurdat.txt) | Kept same structure as starter code from lecture on loading CSV data using COPY; changed specific read-in procedure to handle inconsistent row structures | 1: Both `hurdat_storms` and `hurdat_tracks` load with no errors and the number of tracks is equal to the total number of tracking instances across all storms (`sql/tests/t00-hurdat-table.sql`); 4: Read documentation on HURDAT2 data set to discover inconsistent row structure and checked -999 data inputs, this helped determine to split the load file into two based on the row structure [HURDAT2 Documentation](https://www.nhc.noaa.gov/data/hurdat/hurdat2-format-atl-1851-2021.pdf) |
| 2026-11-15 | building | Adapt API script to handle the CSV retrieval from NOAA storms data; needed to address specific restraints observed in the data | Gemini | [prompt](prompts/2026-11-15-storms.txt) | Kept underlying structure of the provided starter code; created new functions to address monetary damage parsing, timestamps, and Geocoder assignment | 1: All years of data from 1996-2026 (what we wanted for temporal scope) loaded, giving a final table of more that ~1.7M rows (as of 11-15-2026); 5: Traced a record from end to end, comparing what I expect from observing the raw data to the output of SQL query (`sql/tests/t00-storms-table.sql`) |
| 2026-11-15 | building | Add to load_census script to account for negative and string values from raw data which should be treated as missing or numerical data, respectively | Gemini | [prompt](prompts/2026-11-15-census.txt) | Kept the starter code I shared that adapted to Census data; added a function to clean the Census string values to numbers and address negative values as missing data | 7: I wrote a few simple queries to test that negative values were indeed being converted to NULL (so results should not have negatives but may have NULLs) (`sql/tests/t00-census-table.sql`) |
| 2026-11-15 | building | Extend starter code for refresh.py script in order to run refresh step on any/all of the data sources, not just the course example | Gemini | [prompt](prompts/2026-11-15-refresh.txt) | Kept the general structure of the starter code with the fetch, merge, and transactions; added separate functions to refresh each separate data source, as well as conditional statement to choose which of those functions to run based on command line arguments | 4: Checked documentation of [PostgreSQL `UPDATE` Reference](https://www.postgresql.org/docs/current/sql-update.html) and [PostgreSQL `INSERT ... ON CONFLICT`](https://www.postgresql.org/docs/current/sql-insert.html); 6: the AI provided command line runs of the refresh.py script, so testing those produced expected outputs (`sql/tests/t00-test-refresh.txt`) |
| 2026-11-16 | building | Evaluate GHCN observation storage requirements and determine an appropriate geographic scope | ChatGPT | [prompt](prompts/2026-11-16-ghcn-geographic-scope.txt) | Initially considered pulling observations from weather stations across the entire United States; changed the geographic scope to the Southeast and Virginia after estimating storage requirements and observing slow API retrieval times | Estimated PostgreSQL storage of 0.997 GiB for one year and 29.922 GiB for 30 years under the original station selection |
| 2026-11-16 | building | Develop and refine the hurricane ETL script for historical hurricane data | ChatGPT | [prompt](prompts/2026-11-16-hurricane-etl.txt) | Used the existing ETL structure as a starting point and adapted the ingestion process to handle hurricane-specific data and relationships between storms and their tracking observations | Review against the raw HURDAT2 data and existing hurricane table validation tests |
| 2026-11-20 | building | Review and refine SQL analytical queries and corresponding validation tests for syntax, logic, and potential shortcomings | ChatGPT (GPT-6) | prompt | Kept the existing structure of all eight analytical queries and corresponding zero-row tests after reviewing their syntax; identified potential weaknesses in test coverage, including hail month validation, zero-population checks, and hurricane proximity calculations; recommended improvements to strengthen validation without changing the intended analyses | 1: Reviewed SQL syntax and zero-row test structure across sql/queries/q01–q08*.sql and sql/tests/t01–t08*.sql; identified limitations requiring further verification. No database execution or implementation of recommended changes was performed during this review. |


## AI extensions

> One per phase: something AI helped you build that goes beyond what you would otherwise
> have done, verified with check 7 or deeper. One paragraph each: what it is, what it
> does for the client, and how you checked it, with links.

### Building: [name]

### Receiving: [name]

## Receivers' check of a builder entry

> Which builder row you checked, what you did to verify it yourselves, and what you found.
