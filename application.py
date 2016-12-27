from flask import Flask, render_template, request, redirect,jsonify, url_for, flash
app = Flask(__name__)

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

# Connect to Database and create database session
engine = create_engine('sqlite:///catalouge.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/')
def allCategory():
    catgs = session.query(Category).all()
    return render_template("index.html", categories=catgs)

@app.route('/catalouge/<string:catgryname>/items')
def allItems(catgryname):
    category = getCategory(catgryname)
    if category:
        items = session.query(Item).filter_by(category_id=category.id)
        return render_template("items.html", items=items, category=category)
    else:
        return render_template('page not found'), 400

@app.route('/catalouge/item/new', methods=['GET', 'POST'])
def newItem():
    if request.method == 'POST':
        newItem = Item(title=request.form['title'],
                    description=request.form['description'],
                    category_id=request.form['category_id'])
        session.add(newItem)
        session.commit()
        category = session.query(Category).filter_by(id=newItem.category_id).first()
        flash('New Item %s Successfully Created' % newItem.title)
        return redirect(url_for('allItems', catgryname=category.name))
    else:
        categories = session.query(Category).all()
        return render_template("newitem.html", categories=categories)

@app.route('/catalouge/<string:itemtitle>/edit', methods=['GET', 'POST'])
def editItem(itemtitle):
    item = getItemByTitle(itemtitle)
    print item
    categories = session.query(Category).all()
    if item:
        if request.method == 'POST':
            item.title = request.form['title']
            item.description = request.form['description']
            item.category_id = request.form['category_id']
            session.add(item)
            session.commit()
            category = getCategoryById(item.category_id)
            flash('item edited Successfully!')
            return redirect(url_for('allItems', catgryname=category.name))
        else:
            return render_template("edititem.html", item=item, categories=categories)

@app.route('/catalouge/<string:itemtitle>/delete', methods=['GET', 'POST'])
def deleteItem(itemtitle):
    item = getItemByTitle(itemtitle)
    if item:
        category = item.category.name
        if request.method == 'POST':
            session.delete(item)
            session.commit()
            flash('item deleted succssfully!')
            return redirect(url_for('allItems', catgryname=category))
        else:
            return render_template("deleteitem.html", item=item)        
    else:
        return "No element found"        


@app.route('/catalouge/<string:catgryname>/<string:itemtitle>')
def descItem(catgryname, itemtitle):
    return "View item"


def getCategory(name):
    try:
        return session.query(Category).filter_by(name=name).one()
    except:
        return None

def getCategoryById(id):
    print session.query(Category).filter_by(id=id).one()
    try:
        return session.query(Category).filter_by(id=id).one()
    except:
        return None

def getItemByTitle(title):
    try:
        return session.query(Item).filter_by(title=title).one()
    except:
        return None

def getItemById(itemid):
    try:
        return session.query(Item).filter_by(id=itemid).one()
    except:
        return None    


if __name__ == '__main__':
  app.secret_key = 'super_secret_key'
  app.debug = True
  app.run(host = '0.0.0.0', port = 5000)
