from flask import Blueprint, jsonify, render_template

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@main_bp.route('/health')
def health_check():
    """Health check endpoint (used by Docker, from the Week 8 sample)"""
    return jsonify({'status': 'healthy'}), 200
