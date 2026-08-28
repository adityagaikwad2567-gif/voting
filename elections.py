from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services.db_operations import (
    get_elections, get_election, get_active_elections,
    get_candidates_for_election, get_candidate, get_election_results
)

elections_bp = Blueprint('elections', __name__)


@elections_bp.route('/')
def list_elections():
    """List all elections with tabs."""
    active = get_active_elections()
    upcoming = get_elections('Upcoming')
    completed = get_elections('Completed')
    
    return render_template('elections/list.html',
                           active_elections=active,
                           upcoming_elections=upcoming,
                           completed_elections=completed)


@elections_bp.route('/<int:election_id>')
def election_detail(election_id):
    """View election details and candidates."""
    election = get_election(election_id)
    if not election:
        flash('Election not found.', 'warning')
        return redirect(url_for('elections.list_elections'))
    
    candidates = get_candidates_for_election(election_id)
    
    # Check if user has voted
    has_voted = False
    if current_user.is_authenticated:
        from app.services.db_operations import has_voted as check_voted
        has_voted = check_voted(election_id, current_user.id)
    
    return render_template('elections/detail.html',
                           election=election,
                           candidates=candidates,
                           has_voted=has_voted)


@elections_bp.route('/schedule')
def schedule():
    """Election schedule timeline."""
    all_elections = get_elections()
    return render_template('elections/schedule.html', elections=all_elections)


@elections_bp.route('/candidates')
def candidates_list():
    """List all candidates across elections."""
    from app.services.db_operations import get_all_candidates
    candidates, total = get_all_candidates(per_page=100)
    return render_template('elections/candidates.html', candidates=candidates)


@elections_bp.route('/candidate/<int:candidate_id>')
def candidate_detail(candidate_id):
    """View candidate detail."""
    candidate = get_candidate(candidate_id)
    if not candidate:
        flash('Candidate not found.', 'warning')
        return redirect(url_for('elections.candidates_list'))
    
    return render_template('elections/candidate_detail.html', candidate=candidate)


@elections_bp.route('/results')
def results_list():
    """List completed elections with results."""
    completed = get_elections('Completed')
    return render_template('elections/results_list.html', elections=completed)


@elections_bp.route('/results/<int:election_id>')
def results_detail(election_id):
    """View election results with charts."""
    results = get_election_results(election_id)
    if not results:
        flash('Results not available.', 'warning')
        return redirect(url_for('elections.results_list'))
    
    return render_template('elections/results_detail.html', results=results)
