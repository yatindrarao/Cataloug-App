from flask import Flask, render_template, request, redirect,jsonify, url_for, flash
app = Flask(__name__)

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
# from database_setup import Category, Itemm
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

#Connect to Database and create database session
engine = create_engine('sqlite:///catalouge.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/')
def allCategory():
    return "All Categories"

@app.route('/catalouge/<string: catgryname>/item/')
    return "List of Category items"

@app.route('/catalouge/item/new/')
def newItem():
    return "New item"

@app.route('/catalouge/<string: itemname>/edit/')
    return "Edit item"

@app.route('/catalouge/<string: itemname>/delete/')
    return "Delete item"

@app.route('/catalouge/<string: catgryname>/<string: itemname>/')
    return "View item"


if __name__ == '__main__':
  app.secret_key = 'super_secret_key'
  app.debug = True
  app.run(host = '0.0.0.0', port = 5000)
