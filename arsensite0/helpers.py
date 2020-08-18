import requests
import urllib.parse
import time
import datetime

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message):
    return render_template("apology.html", message=message)


def allowed_file(filename):
    ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS