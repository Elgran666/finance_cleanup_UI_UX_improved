# Stock Portfolio Management

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Running the Application](#running-the-application)
5. [Usage](#usage)
   - [Create an account](#create-an-account)
   - [Log in](#log-in)
6. [Managing the Database](#managing-the-database)
7. [Additional Information](#additional-information)


## Introduction
This guide will help you set up and run the Flask application for managing a stock portfolio. Follow the steps below to install necessary dependencies, run the application, and manage the database.

## Prerequisites
- Python 3.x
- pip (Python package installer)

## Installation

1. clone the repository: ```git clone https://github.com/Elgran666/finance_cleanup_UI_UX_improved.git```
2. then cd into it: ```cd finance_cleanup_UI_UX_improved```

4. install flask: ```pip install flask```

## Running the Application

1. run the flask server: ```flask run```


2. open the application
   - open your web browser and navigate to the url provided by the flask server, typically http://127.0.0.1:5000

## Usage

1. create an account
   - open the registration page
   - fill in your desired username and password
   - click "sign up" to create your account

2. log in
   - open the login page
   - enter your username and password
   - click "log in" to access your account

## Managing the Database

if you need to clear the database, follow these steps:

1. open sqlite3: ```sqlite3 finance.db```

2. clear tables

   2.1 clear transactions table: ```delete from transactions;```

   2.2 reset counter for transactions table: ```update sqlite_sequence set seq = 0 where name = 'transactions';```

   2.3 clear users table: ```delete from users;```

   2.4 reset counter for users table: ``` update sqlite_sequence set seq = 0 where name = 'users';```

## Additional Information

- ensure you have a stable internet connection when fetching stock data as the application relies on third-party apis for real-time stock prices
- for any issues or bugs, check the flask server logs for error messages and debug information
