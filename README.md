# FDB (File Database)

FDB is a simple file-based database implemented in Python. It allows you to store, retrieve, update, and delete records in a structured format using JSON serialization. This project is designed for educational purposes and demonstrates basic database operations.

## Features

- **Add Records**: Insert new records into the database.
- **Retrieve Records**: Fetch records by their unique ID.
- **Update Records**: Modify existing records.
- **Delete Records**: Remove records from the database.
- **Filter Records**: Search for records based on indexed fields.
- **Indexing**: Automatically index specified fields for efficient searching.

## Requirements

- Python 3.x
- No external libraries are required.

## Usage

1. **Define a Model**: Create a dictionary that defines the structure of your records, including field names, lengths, and whether they should be indexed.

   ```python
   book_model = {
       "title": {"length": 100, "index": True},
       "author": {"length": 25, "index": True},
       "year": {"length": 4, "index": True},
       "status": {
           "length": 1,
           "default": "1",
       },
   }
   ```

2. **Create a Database Instance**: Initialize the database with a filename and the model.

   ```python
   fdb = FDB("library.txt", book_model)
   ```

3. **Add Records**: Use the `set` method to add records.

   ```python
   fdb.set({
       "title": "Приключения Тома Сойера",
       "author": "Марк Твен",
       "year": "1876",
       "status": "1",
   })
   ```

4. **Retrieve Records**: Use the `get` method to fetch records by ID.

   ```python
   record = fdb.get(1)
   ```

5. **Update Records**: Modify existing records using the `update` method.

   ```python
   fdb.update(1, {"title": "Сказки"})
   ```

6. **Delete Records**: Remove records using the `delete` method.

   ```python
   fdb.delete(1)
   ```

7. **Filter Records**: Search for records using the `filter` method.

   ```python
   results = fdb.filter("title", "Приключения Тома")
   ```

8. **Get All Records**: Retrieve all records from the database.

   ```python
   all_records = fdb.all()
   ```
