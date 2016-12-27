from flask import Flask, render_template, request, redirect,jsonify, url_for, flash, abort
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

CLIENT_ID = json.loads(
            open('client_secret.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalouge Application"

@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
            for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=login_session['state'])

@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.', 401))
        response.headers['Content-Type'] = 'applicaton/json'
        return response
    # Obtain the one time code
    code = request.data
    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secret.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade autherization code'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check the access token is valid
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # IF there is an access token info then abort
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # If user does not exist then create new user
    user_id = getUserID(login_session['email'])
    if not user_id:
        createUser(login_session)
    else:
        login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

@app.route('/gdisconnet')
def gdisconnet():
    access_token = login_session.get('credentials')
    if access_token is None:
        response = make_response(json.dumps('Current User is not connected'),
                401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s'% access_token

    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print "Result is %s"%result
    if result['status'] == '200':
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['credentials']
        response = make_response(json.dumps("Successfully disconnected"), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to disconnet'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response

@app.route('/')
def allCategory():
    catgs = session.query(Category).all()
    if user_signed_in():
        return render_template("index.html", categories=catgs)
    else:
        return render_template("publicindex.html", categories=catgs)

@app.route('/catalouge/<string:catgryname>/items')
def allItems(catgryname):
    category = getCategory(catgryname)
    if category:
        items = session.query(Item).filter_by(category_id=category.id)
        if user_signed_in():
            return render_template("items.html", items=items, category=category)
        else:
            return render_template("publicitems.html", items=items, category=category)
    else:
        return abort(404)

@app.route('/catalouge/<string:itemtitle>')
def descItem(itemtitle):
    item = getItemByTitle(itemtitle)
    if item:
        if user_signed_in() and item.user_id == login_session.get('user_id'):
            return render_template("viewitem.html", item=item)
        else:
            return render_template("publicviewitem.html", item=item)
    else:
        return "No item found"

@app.route('/catalouge/item/new', methods=['GET', 'POST'])
def newItem():
    if user_signed_in():
        categories = session.query(Category).all()
        if request.method == 'POST':
                item = getItemByTitle(request.form['title'])
                if not item:
                    newItem = Item(title=request.form['title'],
                                description=request.form['description'],
                                category_id=request.form['category_id'],
                                user_id=login_session['user_id'])
                    session.add(newItem)
                    session.commit()
                    category = session.query(Category).filter_by(id=newItem.category_id).first()
                    flash('New Item %s Successfully Created' % newItem.title)
                    return redirect(url_for('allItems', catgryname=category.name))
                else:
                    flash('title already exists!')
                    return render_template("newitem.html", categories=categories,
                        title=request.form['title'],
                        description=request.form['description'],
                        category_id=request.form['category_id'])
        else:
            return render_template("newitem.html", categories=categories)
    else:
        message = "You are required to login"
        url = '/login'
        return render_template("alert.html", message=message, url=url)

@app.route('/catalouge/<string:itemtitle>/edit', methods=['GET', 'POST'])
def editItem(itemtitle):
    if user_signed_in():
        item = getItemByTitle(itemtitle)
        categories = session.query(Category).all()
        if item:
            if item.user_id == login_session.get('user_id'):
                if request.method == 'POST':
                    item.title = request.form['title']
                    item.description = request.form['description']
                    item.category_id = request.form['category_id']
                    session.add(item)
                    session.commit()
                    category = getCategoryById(item.category_id)
                    flash('item edited Successfully!')
                    return redirect(url_for('descItem', itemtitle=itemtitle))
                else:
                    return render_template("edititem.html", item=item, categories=categories)
            else:
                message = "You are not authorized to edit this item"
                url = url_for('descItem', itemtitle=item.title)
                return render_template("alert.html", message=message, url=url)
        else:
            return "Not found"
    else:
        message = "You are required to login"
        url = '/login'
        return render_template("alert.html", message=message, url=url)

@app.route('/catalouge/<string:itemtitle>/delete', methods=['GET', 'POST'])
def deleteItem(itemtitle):
    if user_signed_in():
        item = getItemByTitle(itemtitle)
        if item:
            if item.user_id == login_session.get('user_id'):
                category = item.category.name
                if request.method == 'POST':
                    session.delete(item)
                    session.commit()
                    flash('item deleted succssfully!')
                    return redirect(url_for('allItems', catgryname=category))
                else:
                    return render_template("deleteitem.html", item=item)
            else:
                message = "You are not authorized to delete this item"
                url = url_for('descItem', itemtitle=item.title)
                return render_template("alert.html", message=message, url=url)
        else:
            return "No element found"
    else:
        message = "You are required to login"
        url = '/login'
        return render_template("alert.html", message=message, url=url)

@app.route('/catalouge.json')
def allCategoryJSON():
    categories = session.query(Category).all()
    list = []
    for category in categories:
        cat = category.serialize
        items = session.query(Item).filter_by(category_id=category.id)
        cat.update({'Item': [i.serialize for i in items]})
        list.append(cat)

    return jsonify(Category=list)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

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

def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session['email'],
                picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    login_session["user_id"] = user.id
    return user


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(user_email):
    try:
        user = session.query(User).filter_by(email=user_email).one()
        return user.id
    except:
        return None

def user_signed_in():
    return login_session.get('user_id')


if __name__ == '__main__':
  app.secret_key = 'super_secret_key'
  app.debug = True
  app.run(host = '0.0.0.0', port = 5000)
