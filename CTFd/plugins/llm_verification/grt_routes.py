"""Additional LLMV RESTful API routes that are added to CTFd."""
from logging import getLogger

# Third-party imports.
from flask import Blueprint, jsonify, render_template, request
from requests.exceptions import HTTPError

# CTFd imports.
from CTFd.models import Awards, Challenges, Fails, Solves, Submissions, db
from CTFd.plugins import bypass_csrf_protection
from CTFd.utils import get_config
from CTFd.utils.dates import isoformat
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.modes import USERS_MODE, get_model
from CTFd.utils.user import get_current_user

# LLM Verification Plugin module imports.
from .grt_models import GRTSubmission, GRTSolves, LlmChallenge, Pending, Awarded
from .remote_llm import generate_text


log = getLogger(__name__)

def add_routes() -> Blueprint:
    """Add new GRT/LLMV routes to CTFd."""
    # Define HTML blueprints for the LLMV plugin.
    llm_verifications = Blueprint('llm_verifications', __name__, template_folder='templates')

    @llm_verifications.route('/generate', methods=['POST'])
    @bypass_csrf_protection
    def generate_for_challenge():
        """Add a route to CTFd for generating text from a prompt."""
        challenge = LlmChallenge.query.filter_by(id=request.json['challenge_id']).first_or_404()
        #client_llm = ClientLLM(host='127.0.0.1', port=50055)
        preprompt = challenge.preprompt
        complete_prompt = preprompt + request.json['prompt']
        try:
            generated_text = generate_text(complete_prompt)
        except HTTPError as error:
            log.error(f'Error generating text: {error}')
            # Send the error message from the HTTPError as the response to the user.
            response = {'success': False, 'data': {'text': str(error)}}
            return jsonify(response)
        response = {'success': True, 'data': {'text': generated_text}}
        log.info(f'Generated text for challenge "{challenge.name}"')
        return jsonify(response)

    @llm_verifications.route('/submissions/<challenge_id>', methods=['GET'])
    @authed_only
    def submissions_for_challenge(challenge_id):
        """Define a route for for showing users their answer submissions."""
        # Identify the user who would like to see their answer submissions.
        current_user = get_current_user()
        if get_config('user_mode') == USERS_MODE:
            pending = Pending.query.filter_by(challenge_id=challenge_id,
                                                    user_id=current_user.id).all()
        else:
            pending = Pending.query.filter_by(challenge_id=challenge_id,
                                                    team_id=current_user.team_id).all()

        if get_config('user_mode') == USERS_MODE:
            correct = Solves.query.filter(Solves.user_id == current_user.id,
                                               Solves.challenge_id == challenge_id).all()
        else:
            correct = Solves.query.filter(Solves.team_id == current_user.team_id,
                                               Solves.challenge_id == challenge_id).all()

        if get_config('user_mode') == USERS_MODE:
            incorrect = Fails.query.filter(Fails.user_id == current_user.id,
                                                Fails.challenge_id == challenge_id).all()
        else:
            incorrect = Fails.query.filter(Fails.team_id == current_user.team_id,
                                                Fails.challenge_id == challenge_id).all()

        if get_config('user_mode') == USERS_MODE:
            awarded = Awarded.query.filter(Awarded.user_id == current_user.id,
                                                Awarded.challenge_id == challenge_id).all()
        else:
            awarded = Awarded.query.filter(Awarded.team_id == current_user.team_id,
                                                Awarded.challenge_id == challenge_id).all()

        pending = [{'provided': p.provided, 'date': isoformat(p.date)} for p in pending]
        log.debug(f'User "{current_user.id}" has {len(pending)} pending submissions for challenge "{challenge_id}"')
        correct = [{'provided': c.provided, 'date': isoformat(c.date)} for c in correct]
        log.debug(f'User "{current_user.id}" has {len(correct)} correct submissions for challenge "{challenge_id}"')
        awarded = [{'provided': a.provided, 'date': isoformat(a.date)} for a in awarded]
        log.debug(f'User "{current_user.id}" has {len(awarded)} awarded submissions for challenge "{challenge_id}"')
        incorrect = [{'provided': i.provided, 'date': isoformat(i.date)} for i in incorrect ]
        log.debug(f'User "{current_user.id}" has {len(incorrect)} incorrect submissions for challenge "{challenge_id}"')
        response = {'success': True,
                                    'data': {'pending': pending,
                                                'correct': correct,
                                                'awarded': awarded,
                                                'incorrect': incorrect}}
        log.info(f'Showed user {current_user.id} '
                    f'their answer submissions for challenge "{challenge_id}"')
        return jsonify(response)

    @llm_verifications.route('/admin/submissions/pending', methods=['GET'])
    @admins_only
    def view_pending_submissions():
        """Add an admin route for viewing answer submissions that haven't been reviewed."""
        filters = {'type': 'pending'}
        curr_page = abs(int(request.args.get('page', 1, type=int)))
        results_per_page = 50
        page_start = results_per_page * (curr_page - 1)
        page_end = results_per_page * (curr_page - 1) + results_per_page
        sub_count = Submissions.query.filter_by(**filters).count()
        page_count = int(sub_count / results_per_page) + (sub_count % results_per_page > 0)
        Model = get_model()
        submissions = (Submissions.query.add_columns(Submissions.id,
                                                          Submissions.type,
                                                          Submissions.challenge_id,
                                                          Submissions.provided,
                                                          Submissions.account_id,
                                                          Submissions.date,
                                                          Challenges.name.label('challenge_name'),
                                                          Model.name.label('team_name'),
                                                          GRTSubmission.prompt,
                                                          GRTSubmission.text).select_from(Submissions)
                                                                             .filter_by(**filters)
                                                                             .join(Challenges)
                                                                             .join(Model)
                                                                             .join(GRTSubmission, GRTSubmission.id == Submissions.id)
                                                                             .order_by(Submissions.date.desc())
                                                                             .slice(page_start, page_end)
                                                                             .all())
        log.info(f'Showed (admin) {len(submissions)} pending answer submissions')
        return render_template('verify_submissions.html',
                                submissions=submissions,
                                page_count=page_count,
                                curr_page=curr_page)

    @llm_verifications.route('/admin/submissions/solved', methods=['GET'])
    @admins_only
    def view_solved_submissions():
        """Add an admin route for viewing answer submissions that have been marked as correct."""
        filters = {'success': True}
        curr_page = abs(int(request.args.get('page', 1, type=int)))
        results_per_page = 50
        page_start = results_per_page * (curr_page - 1)
        page_end = results_per_page * (curr_page - 1) + results_per_page
        sub_count = GRTSolves.query.filter_by(**filters).count()
        page_count = int(sub_count / results_per_page) + (sub_count % results_per_page > 0)
        Model = get_model()
        submissions = (GRTSolves.query.add_columns(GRTSolves.id,
                                                        GRTSolves.challenge_id,
                                                        GRTSolves.prompt,
                                                        GRTSolves.account_id,
                                                        GRTSolves.text,
                                                        GRTSolves.date,
                                                        Challenges.name.label('challenge_name'),
                                                        Challenges.description.label('challenge_description'),
                                                        Model.name.label('team_name')).select_from(GRTSolves)
                                                                                        .filter_by(**filters)
                                                                                        .join(Challenges)
                                                                                        .join(Model)
                                                                                        .order_by(GRTSolves.date.desc())
                                                                                        .slice(page_start, page_end)
                                                                                        .all())
        log.info(f'Showed (admin) solved answer submissions')
        return render_template('solved_submissions.html',
                               submissions=submissions,
                               page_count=page_count,
                               curr_page=curr_page)

    @llm_verifications.route('/admin/verify_submissions/<submission_id>/<status>', methods=['POST'])
    @admins_only
    def verify_submissions(submission_id, status):
        """Add a route for admins to mark answer attempts as correct or incorrect."""
        submission = Submissions.query.filter_by(id=submission_id).first_or_404()
        grt_submission = GRTSubmission.query.filter_by(id=submission_id).first_or_404()
        if status == 'solve':
            solve = Solves(user_id=submission.user_id,
                           team_id=submission.team_id,
                           challenge_id=submission.challenge_id,
                           ip=submission.ip,
                           provided=submission.provided,
                           date=submission.date)
            db.session.add(solve)
            # Get rid of pending submissions for the challenge
            Submissions.query.filter(Submissions.challenge_id == submission.challenge_id,
                                     Submissions.team_id == submission.team_id,
                                     Submissions.user_id == submission.user_id,
                                     Submissions.type == 'pending').delete()
            solve = GRTSolves(success=True,
                              challenge_id=submission.challenge_id,
                              text=grt_submission.text,
                              prompt=grt_submission.prompt,
                              date=submission.date,
                              user_id=submission.user_id,
                              team_id=submission.team_id)
            db.session.add(solve)
        elif status == 'award':
            awarded = Awarded(user_id=submission.user_id,
                              team_id=submission.team_id,
                              challenge_id=submission.challenge_id,
                              ip=submission.ip,
                              provided=submission.provided)
            award = Awards(user_id=submission.user_id,
                           team_id=submission.team_id,
                           name='Submission',
                           description='Correct Submission for {name}'.format(name=submission.challenge.name),
                           value=request.args.get('value', 0),
                           category=submission.challenge.category)
            db.session.add(awarded)
            db.session.add(award)
            solve = GRTSolves(success=True,
                              challenge_id=submission.challenge_id,
                              text=grt_submission.text,
                              prompt=grt_submission.prompt,
                              date=submission.date,
                              user_id=submission.user_id,
                              team_id=submission.team_id)
            db.session.add(solve)
        elif status == 'fail':
            wrong = Fails(user_id=submission.user_id,
                          team_id=submission.team_id,
                          challenge_id=submission.challenge_id,
                          ip=submission.ip,
                          provided=submission.provided,
                          date=submission.date)
            db.session.add(wrong)
            solve = GRTSolves(success=False,
                              challenge_id=submission.challenge_id,
                              text=grt_submission.text,
                              prompt=grt_submission.prompt,
                              date=submission.date,
                              user_id=submission.user_id,
                              team_id=submission.team_id)
            db.session.add(solve)
        else:
            return jsonify({'success': False})
        db.session.delete(submission)
        db.session.commit()
        db.session.close()
        log.info(f'Marked answer submission "{submission_id}" as "{status}"')
        return jsonify({'success': True})

    return llm_verifications
