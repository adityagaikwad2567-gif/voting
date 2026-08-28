from flask import Blueprint, render_template, request

info_bp = Blueprint('info', __name__)


@info_bp.route('/how-to-vote')
def how_to_vote():
    """How to vote guide."""
    return render_template('info/how_to_vote.html')


@info_bp.route('/eligibility')
def eligibility():
    """Voter eligibility information."""
    return render_template('info/eligibility.html')


@info_bp.route('/documents')
def documents():
    """Documents required."""
    return render_template('info/documents.html')


@info_bp.route('/faq')
def faq():
    """Frequently Asked Questions."""
    return render_template('info/faq.html')


@info_bp.route('/contact')
def contact():
    """Contact / Help page."""
    return render_template('info/contact.html')


@info_bp.route('/about')
def about():
    """About the project."""
    return render_template('info/about.html')


@info_bp.route('/privacy')
def privacy():
    """Privacy policy."""
    return render_template('info/privacy.html')


@info_bp.route('/terms')
def terms():
    """Terms of use."""
    return render_template('info/terms.html')
