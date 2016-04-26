from flask import Flask, render_template, flash, redirect, session, url_for, request, g, jsonify
from app import app
import os.path

@app.route('/')
@app.route('/index')
def index():
    return render_template('home.html', title='Home - Python Recipes')

################################################################################
################################################################################

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

