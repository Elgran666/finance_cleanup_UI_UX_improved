import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


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
    user_id = session['user_id']

    # Fetch transactions to calculate net shares
    transactions = db.execute("""
        SELECT symbol, SUM(shares) as net_shares
        FROM transactions WHERE user_id = ? GROUP BY symbol
    """, user_id)

    total_stock_value = 0
    current_stock_values = {}
    combined_stocks_in_portfolio = {}

    for transaction in transactions:
        symbol = transaction['symbol']
        net_shares = transaction['net_shares']
        combined_stocks_in_portfolio[symbol] = net_shares  # Store net shares correctly

        if net_shares > 0:  # Only show stocks that are currently owned
            stock_info = lookup(symbol)
            if stock_info:
                stock_value = round(stock_info['price'] * net_shares, 2)
                current_stock_values[symbol] = stock_value
                total_stock_value += stock_value

    cash_info = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    total_cash_value = round(cash_info[0]['cash'], 2) if cash_info else 0
    total_portfolio_value = round(total_stock_value + total_cash_value, 2)

    return render_template("index.html", total_stock_value=total_stock_value,
                           total_cash_value=total_cash_value,
                           total_portfolio_value=total_portfolio_value,
                           current_stock_values=current_stock_values,
                           combined_stocks_in_portfolio=combined_stocks_in_portfolio)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Handle the purchase of stock shares."""
    if request.method == "GET":
        # Display the buy form
        return render_template("buy.html")

    # Processing form data when form is submitted
    if request.method == "POST":
        stock_to_buy = request.form.get("symbol")
        stock_amount = request.form.get("shares")

        # Validation for stock symbol input
        if not stock_to_buy:
            flash("No Stock symbol provided.", "error")
            return redirect(url_for("buy"))

        # Validation for stock amount input
        if not stock_amount or not stock_amount.isdigit() or int(stock_amount) <= 0:
            flash("Invalid amount provided. Please enter a positive number.", "error")
            return redirect(url_for("buy"))

        stock_amount = int(stock_amount)
        if stock_amount >= 1000:
            flash("You can only buy up to 999 shares at a time.", "error")
            return redirect(url_for("buy"))

        # Fetch stock data from a third-party API
        stock_data = lookup(stock_to_buy)
        if not stock_data:
            flash("Stock not found. Please provide a valid symbol.", "error")
            return redirect(url_for("buy"))

        # Calculate total cost of purchase
        total_price = round(stock_data['price'] * stock_amount, 2)
        user_id = session['user_id']
        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]['cash']

        # Check if user has enough cash to make the purchase
        if user_cash < total_price:
            flash("Not enough balance to complete the purchase.", "error")
            return redirect(url_for("buy"))

        # Database operations for updating transactions and user balance
        # Insert the transaction as uppercase symbol
        db.execute("INSERT INTO transactions (user_id, transaction_type, symbol, shares, price) VALUES (?, 'buy', ?, ?, ?)",
                   user_id, stock_to_buy.upper(), stock_amount, stock_data['price'])
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total_price, user_id)

        flash("Purchase successful!", "success")
        return redirect("/")

    return redirect(url_for("index"))


@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    user_id = session['user_id']
    # Fetch all transactions for the logged-in user ordered by timestamp.
    transaction_history = db.execute(
        "SELECT transaction_type, symbol, shares, price, strftime('%Y-%m-%d %H:%M:%S', timestamp) as timestamp FROM transactions WHERE user_id = ? ORDER BY timestamp DESC",
        user_id
    )

    return render_template("history.html", transaction_history=transaction_history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Process the login form
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("login.html")

        user = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(user) != 1 or not check_password_hash(user[0]['hash'], password):
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        session['user_id'] = user[0]['id']
        flash("Login successful!", "success")
        return redirect("/")
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

    # Handling GET request to show the form
    if request.method == "GET":
        return render_template("quote.html")

    # Handling POST request when form is submitted
    if request.method == "POST":
        # Fetching the stock symbol from the form data
        symbol = request.form.get("symbol")

        # If no symbol was provided, flash a warning message and redirect to the same form
        if not symbol:
            flash("Must provide a stock symbol.", "warning")  # Flash a message with the category 'warning'
            return redirect(url_for('quote'))  # Redirect to the quote page to prompt user again

        # Look up the stock symbol using a helper function (e.g., hitting an API)
        stock_data = lookup(symbol)

        # If the lookup function returns None, the symbol was not found
        if stock_data is None:
            flash("Stock not found. Please try a valid symbol.", "warning")  # Provide feedback about the invalid symbol
            return redirect(url_for('quote'))  # Redirect to try again

        # If the symbol is found and data is retrieved, display the stock information
        # The stock data is passed to the same template to be displayed
        return render_template("quote.html", stock_data=stock_data)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration with GET to show the form and POST to process the form data."""

    # Show the registration form when accessed via GET request
    if request.method == "GET":
        return render_template("registration.html")

    # Process registration data when form is submitted via POST
    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmed_password = request.form.get("confirmation")

        # Validate form inputs
        if not username:
            flash("Missing username.", "warning")
            return redirect("/register")
        if not password:
            flash("Missing password.", "warning")
            return redirect("/register")
        if not confirmed_password:
            flash("Please confirm your password.", "warning")
            return redirect("/register")
        if password != confirmed_password:
            flash("Passwords do not match.", "warning")
            return redirect("/register")

        # Check if the username already exists
        user_exists = db.execute("SELECT * FROM users WHERE username = ?", username)
        if user_exists:
            flash("Username already taken.", "warning")
            return redirect("/register")

        # Register the new user
        hashed_password = generate_password_hash(password)
        user_id = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hashed_password)

        # Log in the user automatically after registration
        session['user_id'] = user_id
        flash("Registered successfully! Welcome, " + username + "!", "success")
        return redirect("/")

    # Redirect to the home page if any other method is used
    return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Handle the selling of shares."""
    user_id = session['user_id']  # Get the user ID from the session

    def get_portfolio(user_id):
        # Execute SQL query to retrieve all transactions for the given user ID
        transactions = db.execute(
            "SELECT symbol, shares FROM transactions WHERE user_id = ? ORDER BY symbol", user_id
        )

        # Initialize a dictionary to keep track of net shares per stock symbol
        portfolio = {}

        # Iterate through each transaction to compute net shares
        for transaction in transactions:
            symbol = transaction['symbol']
            shares = transaction['shares']

            # Initialize the symbol in the portfolio dictionary if it's not already present
            if symbol not in portfolio:
                portfolio[symbol] = 0

            # Update the net shares count
            portfolio[symbol] += shares

        # Filter and return the dictionary to include only stocks with positive net shares
        positive_stocks = {symbol: count for symbol, count in portfolio.items() if count > 0}
        return positive_stocks

    # Aggregate shares by stock symbol
    combined_stocks_in_portfolio = get_portfolio(user_id)

    if request.method == "GET":
        # Fetch current prices for the aggregated stocks
        current_stock_values = {
            stock: round(lookup(stock)['price'] * amount, 2)
            for stock, amount in combined_stocks_in_portfolio.items() if amount > 0
        }

        # Render sell page with stock data
        return render_template("sell.html", current_stock_values=current_stock_values, combined_stocks_in_portfolio=combined_stocks_in_portfolio)

    elif request.method == "POST":
        symbol = request.form.get('symbol').upper()
        shares_to_sell = int(request.form.get('shares'))

        if not symbol or shares_to_sell <= 0:
            flash("Please select a valid stock and number of shares to sell.", "error")
            return redirect("/sell")

        # Check stock ownership and amount
        owned_shares = combined_stocks_in_portfolio.get(symbol, 0)
        if shares_to_sell > owned_shares:
            flash("You do not own enough shares to complete this transaction.", "error")
            return redirect("/sell")

        # Proceed with selling
        stock_info = lookup(symbol)
        if not stock_info:
            flash("Failed to fetch stock information.", "error")
            return redirect("/sell")

        sale_value = round(stock_info['price'] * shares_to_sell, 2)
        db.execute("INSERT INTO transactions (user_id, transaction_type, symbol, shares, price) VALUES (?, 'sell', ?, -?, ?)",
                   user_id, symbol, shares_to_sell, stock_info['price'])
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", sale_value, user_id)

        flash("Sold successfully!", "success")
        return redirect("/")

    return redirect("/")




@app.route("/password", methods=["GET", "POST"])
@login_required
def password():
    """Allow users to change their password."""
    if request.method == 'GET':
        # Display the password change form
        return render_template("password.html")

    # Process form data on POST
    old_password = request.form.get("old_password")
    new_password = request.form.get("new_password")
    confirmed_new_password = request.form.get("confirmed_new_password")

    # Check for input completeness
    if not old_password or not new_password or not confirmed_new_password:
        flash("Please fill out all fields.", "warning")
        return redirect(url_for("password"))

    user_id = session['user_id']
    user_hash = db.execute("SELECT hash FROM users WHERE id = ?", user_id)[0]['hash']

    # Validate the old password
    if not check_password_hash(user_hash, old_password):
        flash("The old password is incorrect.", "error")
        return redirect(url_for("password"))

    # Check if new password and confirmation match
    if new_password != confirmed_new_password:
        flash("New password and confirmation do not match.", "error")
        return redirect(url_for("password"))

    # Update user's password
    new_password_hash = generate_password_hash(new_password)
    db.execute("UPDATE users SET hash = ? WHERE id = ?", new_password_hash, user_id)
    flash("Password updated successfully!", "success")
    return redirect(url_for("password"))
