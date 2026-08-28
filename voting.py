from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services.db_operations import (
    get_active_elections, get_election, get_candidates_for_election,
    cast_vote, has_voted, get_voter_vote_history, get_user_by_voter_id
)
from app.utils.helpers import log_user_action

voting_bp = Blueprint('voting', __name__)


@voting_bp.route('/')
@login_required
def index():
    """Online voting hub."""
    active_elections = get_active_elections()
    return render_template('voting/index.html', active_elections=active_elections)


@voting_bp.route('/active')
@login_required
def active_elections():
    """View active elections."""
    elections = get_active_elections()
    return render_template('voting/active.html', active_elections=elections)


@voting_bp.route('/cast/<int:election_id>', methods=['GET', 'POST'])
@login_required
def cast(election_id):
    """Cast vote for an election."""
    election = get_election(election_id)
    if not election:
        flash('Election not found.', 'warning')
        return redirect(url_for('voting.active_elections'))
    
    if election['status'] != 'Active':
        flash('This election is not currently active.', 'warning')
        return redirect(url_for('voting.active_elections'))
    
    if has_voted(election_id, current_user.id):
        flash('You have already voted in this election.', 'info')
        return redirect(url_for('voting.status'))
    
    candidates = get_candidates_for_election(election_id)
    
    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id')
        if not candidate_id:
            flash('Please select a candidate.', 'warning')
            return render_template('voting/cast.html', election=election, candidates=candidates)
        
        # Store selection for confirmation
        return redirect(url_for('voting.confirm', election_id=election_id, candidate_id=candidate_id))
    
    return render_template('voting/cast.html', election=election, candidates=candidates)


@voting_bp.route('/confirm/<int:election_id>/<int:candidate_id>', methods=['GET', 'POST'])
@login_required
def confirm(election_id, candidate_id):
    """Confirm vote before submission."""
    election = get_election(election_id)
    if not election or election['status'] != 'Active':
        flash('This election is not currently active.', 'warning')
        return redirect(url_for('voting.active_elections'))
    
    if has_voted(election_id, current_user.id):
        flash('You have already voted in this election.', 'info')
        return redirect(url_for('voting.status'))
    
    candidate = None
    candidates = get_candidates_for_election(election_id)
    for c in candidates:
        if c['id'] == candidate_id:
            candidate = c
            break
    
    if not candidate:
        flash('Invalid candidate selected.', 'warning')
        return redirect(url_for('voting.cast', election_id=election_id))
    
    if request.method == 'POST':
        vote_id, result = cast_vote(election_id, current_user.id, candidate_id)
        
        if vote_id:
            log_user_action(current_user.id, 'VOTE_CAST', 'vote', vote_id)
            flash('Your vote has been recorded successfully!', 'success')
            return render_template('voting/success.html',
                                   election=election,
                                   candidate=candidate,
                                   reference_code=result)
        else:
            flash(f'Failed to record vote: {result}', 'danger')
            return redirect(url_for('voting.cast', election_id=election_id))
    
    return render_template('voting/confirm.html', election=election, candidate=candidate)


@voting_bp.route('/status')
@login_required
def status():
    """Voting status."""
    return render_template('voting/status.html')


@voting_bp.route('/history')
@login_required
def history():
    """Voting history."""
    vote_history = get_voter_vote_history(current_user.id)
    return render_template('voting/history.html', vote_history=vote_history)
