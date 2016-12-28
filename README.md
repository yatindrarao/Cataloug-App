# Catalouge Application
Catalouge application gives you capability to create a catalouge of different
categories with items.

## Feature
- User can create, update and delete their items
- Need to sign in to create, edit and delete items
- User can only edit and delete his own items
- Supports 3rd party login using Google account

## Technologies
This app uses:

- Python 2.7
- Flask
- SqlAlchemy ORM
- Sqlite Database

## Getting Started
### Step 1
Take clone from www.github.com and change to project folder.
```
$ git clone github.com
$ cd catalouge
```

### Step 2
Now first setup the database and seed database with categories.
```
$ python database_setup.py
$ python setupcategories.py
```
