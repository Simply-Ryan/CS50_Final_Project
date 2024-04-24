import csv
import datetime
import pytz
import requests
import urllib
import uuid

from flask import redirect, render_template, request, session

def error(msg, code):
    return render_template("error.html", message=msg, code=code)

def usd(value):
    # Format values as USD
    return f"${value:,.2f}"