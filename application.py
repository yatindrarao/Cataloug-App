import requests
from flask import Flask, render_template, request, redirect, jsonify, url_for,\
 flash, abort
from flask import session as login_session
from flask import make_response

from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json

app = Flask(__name__)
# Connect to Database and create database session
engine = create_engine('sqlite:///catalouge.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Store client id of application registered with Google
CLIENT_ID = json.loads(
            open('client_secret.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalouge Application"


@app.route('/login')
def showLogin():
    # Check if user is logged in
    if not user_signed_in():
        state = ''.join(
            random.choice(string.ascii_uppercase + string.digits)
            for x in xrange(32)
        )
        login_session['state'] = state
        return render_template('login.html', STATE=login_session['state'])
    else:
        flash('You are already connected')
        return redirect(url_for('allCategory'))


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
        response = make_response(json.dumps(
                    'Current user is already connected.'), 200)
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
    # If user does not exist then create new user and store user_id in
    # login_session
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
    output += ''' " style = "width: 300px; height: 300px;border-radius: 150px;
                -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '''
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


@app.route('/logout')
def gdisconnet():
    access_token = login_session.get('credentials')
    # Check if access token is present or not
    if access_token is None:
        flash("Current user is not connected")
        return redirect(url_for('allCategory'))
    # Request google for logging out user
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token

    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # After successful request removes all variables in login_session
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['credentials']
        flash("Successfully disconnected")
        return redirect(url_for('allCategory'))
    else:
        # Some error
        flash("Failed to disconnet")
        return redirect(url_for('allCategory'))


@app.route('/')
def allCategory():
    # Index page
    catgs = session.query(Category).all()
    # fetch latest items with limit 6 results
    items = session.query(Item).order_by(desc(Item.created_at)).limit(6)
    return render_template(
        "index.html",
        categories=catgs,
        items=items,
        user_signed_in=user_signed_in()
    )


@app.route('/catalouge/<string:catgryname>/items')
def allItems(catgryname):
    # All items of particular category
    category = getCategory(catgryname)
    if category:
        items = session.query(Item).filter_by(
            category_id=category.id
            ).order_by(desc(Item.created_at))
        catgs = session.query(Category).all()
        return render_template(
            "items.html",
            items=items,
            category=category,
            categories=catgs,
            user_signed_in=user_signed_in()
        )
    else:
        return abort(404)


@app.route('/catalouge/<string:itemtitle>')
def descItem(itemtitle):
    # Show details of item such as title and description
    item = getItemByTitle(itemtitle)
    if item:
        owner = item.user_id == login_session.get('user_id')
        return render_template(
            "viewitem.html",
            item=item,
            owner=owner,
            user_signed_in=user_signed_in()
        )
    else:
        return "No item found"


@app.route('/catalouge/item/new', methods=['GET', 'POST'])
def newItem():
    # Redirect to login if user is not logged in
    if user_signed_in():
        categories = session.query(Category).all()
        if request.method == 'POST':
                item = getItemByTitle(request.form['title'])
                if not item:
                    newItem = Item(
                        title=request.form['title'],
                        description=request.form['description'],
                        category_id=request.form['category_id'],
                        user_id=login_session['user_id']
                    )
                    session.add(newItem)
                    session.commit()
                    category = session.query(Category).filter_by(
                                id=newItem.category_id).first()
                    flash('New Item %s Successfully Created' % newItem.title)
                    return redirect(url_for(
                        'allItems',
                        catgryname=category.name)
                    )
                else:
                    # Validates uniquness of Item by title
                    flash('title already exists!')
                    return render_template(
                        "newitem.html",
                        categories=categories,
                        title=request.form['title'],
                        description=request.form['description'],
                        category_id=request.form['category_id']
                    )
        else:
            # Render form for new item
            return render_template(
                "newitem.html",
                categories=categories,
                user_signed_in=user_signed_in()
            )
    else:
        message = "You are required to login"
        url = '/login'
        return render_template("alert.html", message=message, url=url)


@app.route('/catalouge/<string:itemtitle>/edit', methods=['GET', 'POST'])
def editItem(itemtitle):
    # Redirects to Login page if user is not logged in
    if user_signed_in():
        item = getItemByTitle(itemtitle)
        categories = session.query(Category).all()
        if item:
            # Validates athorization of user to edit this item
            if item.user_id == login_session.get('user_id'):
                if request.method == 'POST':
                    item.title = request.form['title']
                    item.description = request.form['description']
                    item.category_id = request.form['category_id']
                    session.add(item)
                    session.commit()
                    category = getCategoryById(item.category_id)
                    flash('item edited Successfully!')
                    return redirect(url_for('descItem', itemtitle=item.title))
                else:
                    # Render Edit Item form
                    return render_template(
                        "edititem.html",
                        item=item,
                        categories=categories,
                        user_signed_in=user_signed_in()
                    )
            else:
                message = "You are not authorized to edit this item"
                url = url_for('descItem', itemtitle=item.title)
                return render_template("alert.html", message=message, url=url)
        else:
            # If no element is found by title given
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
            # Validates authorization of User to delete this item
            if item.user_id == login_session.get('user_id'):
                category = item.category.name
                if request.method == 'POST':
                    session.delete(item)
                    session.commit()
                    flash('item deleted succssfully!')
                    return redirect(url_for('allItems', catgryname=category))
                else:
                    # Render delete item form
                    return render_template(
                        "deleteitem.html",
                        item=item,
                        user_signed_in=user_signed_in()
                    )
            else:
                # Redirect to view item page if user is not authorized
                message = "You are not authorized to delete this item"
                url = url_for('descItem', itemtitle=item.title)
                return render_template("alert.html", message=message, url=url)
        else:
            # If no element is found with given title
            return "No element found"
    else:
        message = "You are required to login"
        url = '/login'
        return render_template("alert.html", message=message, url=url)


@app.route('/catalouge.json')
def allCategoryJSON():
    # Fetch all data in JSON format
    categories = session.query(Category).all()
    list = []
    for category in categories:
        cat = category.serialize
        items = session.query(Item).filter_by(category_id=category.id)
        cat.update({'Item': [i.serialize for i in items]})
        list.append(cat)

    return jsonify(Category=list)


@app.route('/catalouge/<string:itemtitle>.json')
def itemJSON(itemtitle):
    # Fetch item data in JSON format
    item = getItemByTitle(itemtitle)
    if item:
        cat = {'category': item.category.name}
        output = item.serialize
        output.update(cat)
        return jsonify(Item=output)
    else:
        response = jsonify({'code': 404,
                            'message': 'No interface defined for URL '})
        response.status_code = 404
        return response


# Handles error page
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# Find category by it's name
def getCategory(name):
    try:
        return session.query(Category).filter(Category.name == name).one()
    except:
        return None


# Find category by it's id
def getCategoryById(id):
    print session.query(Category).filter_by(id=id).one()
    try:
        return session.query(Category).filter_by(id=id).one()
    except:
        return None


# Find item by it's title
def getItemByTitle(title):
    try:
        return session.query(Item).filter_by(title=title).one()
    except:
        return None


# Find category by it's id
def getItemById(itemid):
    try:
        return session.query(Item).filter_by(id=itemid).one()
    except:
        return None


def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
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
    app.debug = False
    app.run()
