import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    id = session["user_id"]
    users = db.execute("SELECT * FROM users WHERE id = ?", id)
    stocks = db.execute("SELECT symbol, share, cash FROM users WHERE id = ?", id)
    #if there is no history then
    if users[0]["symbol"] is None:
        return render_template("index.html", share = None, symbol = None, total = None, cash = 0, price = users[0]["cash"], name = users[0]["name"])

    else:
        #if there is a history od stock then reutrn this
        cash = lookup(stocks[0]["symbol"])
        return render_template("index.html", share = stocks[0]["share"], symbol=stocks[0]["symbol"], total=stocks[0]["cash"], cash=cash, price = users[0]["cash"], name = users[0]["name"])



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        #check for symbol valied or not
        symbol = lookup(request.form.get("symbol"))
        if symbol == None or not request.form.get("symbol"):
            return apology("invalied symbol",400)
        else:
            share = float(request.form.get("shares"))
            if share < 0 or share % 1 != 0 or not share:
                return apology("invalied share",400)
            id = session["user_id"]
            cash = db.execute("SELECT * FROM users WHERE id = ?", id)
            price = share * symbol["price"]

            #check for sufficient cash
            if not cash[0]["cash"] < price:
                cash[0]["cash"] = cash[0]["cash"] - price
                total = round(cash[0]["cash"] + price, 2)

                #updating the table
                db.execute("update users set cash = ?, symbol = ?,name = ?, price = ?, share = ? where id = ?", cash[0]["cash"], symbol["symbol"], symbol["name"], symbol["price"],share, id,)

                return render_template("bought.html",symbol = symbol, share = share,price = price, cash = round(cash[0]["cash"], 2), total = total)
            else:
                return apology("not sufficient cash",400)


    #for get method
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    id = session["user_id"]
    users = db.execute("SELECT * FROM users WHERE id = ?", id)
    stocks = db.execute("SELECT symbol, share, cash FROM users WHERE id = ?", id)
    #if there is no history then
    if users[0]["symbol"] is None:
        return apology("sorry no history yet",200)

    else:
        #if there is a history od stock then reutrn this
        cash = lookup(stocks[0]["symbol"])
        return render_template("index.html", share = stocks[0]["share"], symbol=stocks[0]["symbol"], total=stocks[0]["cash"], cash=cash, price = users[0]["cash"], name = users[0]["name"])


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))
        if quote == None:
            return apology("invalied symbol",400)
        else:
            return render_template("quoted.html", quote=quote)
    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        #ensure confirm and password are same
        elif request.form.get("password")!=request.form.get("confirmation"):
            return apology("password mismatch",400)

        # Query database for username
        if not db.execute("SELECT username FROM users WHERE username = ?", request.form.get("username")):
        #if not len(rows) !=0:
            password = generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users(username, hash) values(?, ?)", request.form.get("username"), password)
            # Redirect user to home page
            return redirect("/")

        else:
            return apology("user exist",400)


    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")




@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    id = session["user_id"]
    if request.method == "POST":

        quote = lookup(request.form.get("symbol"))

        # Check if the symbol exists
        if quote == None:
            return apology("invalid symbol", 400)

        # Check if shares was a positive integer
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("shares must be a positive integer", 400)

        # Check if # of shares requested was 0
        if shares <= 0:
            return apology("can't sell less than or 0 shares", 400)

        # Check if we have enough shares
        symbol=request.form.get("symbol")
        stock = db.execute("SELECT SUM(share) as total_shares FROM users WHERE id = ? AND symbol = ? GROUP BY symbol",id, symbol)

        if len(stock) != 1 or stock[0]["total_shares"] <= 0 or stock[0]["total_shares"] < shares:
            return apology("can't sell less than 0 or more than you own", 400)

        # Query database for username
        rows = db.execute("SELECT cash FROM users WHERE id = ?", id)

        # How much $$$ the user still has in her account
        cash_remaining = rows[0]["cash"]
        price_per_share = quote["price"]

        # Calculate the price of requested shares
        total_price = price_per_share * shares

        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?",total_price, id)

        symbol=request.form.get("symbol")
        share = request.form.get("shares")
        price = lookup(symbol)
        cash = price["price"] * int(share)
        db.execute("INSERT INTO transition1 (id, symbol, share, price) VALUES(?, ?, ?, ?)",id, symbol, share, cash)

        user = db.execute("select * from users where id = ?", id)
        return render_template("sold.html", user = user)

    else:
        stocks = db.execute("SELECT symbol, SUM(share) as total_shares FROM users WHERE id = ? GROUP BY symbol HAVING share > 0", id)

        return render_template("sell.html", stocks=stocks)