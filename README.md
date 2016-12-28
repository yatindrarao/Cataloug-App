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
```
$ git clone https://github.com/yatindrarao/Cataloug-App.git
$ cd Cataloug-App
```

### Step 2
Setup the database and seed database with categories.
```
$ python database_setup.py
$ python setupcategories.py
```
This will create our database in `catalouge.db` in current directory.
### Step 3
Run the application by following commands.
```
$ python applcation.py
```
This will start the application on http://localhost:5000 by default.

## License

This project is available under MIT License.
