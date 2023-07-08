"""Additional LLMV RESTful API routes that are added to CTFd."""
from logging import getLogger

# Third-party imports.
from flask import Blueprint, jsonify, render_template, request
from requests.exceptions import HTTPError

# CTFd imports.
from CTFd.models import Awards, Challenges, Fails, Solves, Submissions, db
from CTFd.plugins import bypass_csrf_protection
from CTFd.utils.dates import isoformat
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.modes import get_model
from CTFd.utils.user import get_current_user

# LLM Verification Plugin module imports.
from .grt_models import GRTSubmission, GRTSolves, LlmChallenge, Pending, Awarded
from .remote_llm import generate_text
from .utils import get_filter_by_mode


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
        log.debug(f'User "{get_current_user().name}" '
                  f'requested their answer submissions for challenge "{challenge_id}"')
        # Make a place to put answer submissions from the database.
        answer_submissions = {Pending: {'extracted_results': None},
                                                              Solves:  {'extracted_results': None},
                                                              Awarded: {'extracted_results': None},
                                                              Fails:   {'extracted_results': None}}
        # For each answer submission of a given type (e.g. "Pending", "Solves", "Awarded", "Fails")...
        for submission_type in answer_submissions:
            # Define query filters for the current user/team and the current user/team's ID.
            mode_uid, current_uid = get_filter_by_mode(submission_type)
            # Query the database for the user's answer submissions for this challenge.
            query_results = submission_type.query.filter(mode_uid == current_uid,
                                                              submission_type.challenge_id == challenge_id).all()
            log.debug(f'User "{get_current_user().name}" '
                      f'has {len(query_results)} "{submission_type}" '
                      f'answer submissions for challenge "{challenge_id}"')
            # Extract the values of the `provided` and `date` columns from each answer submission.
            answer_submissions[submission_type]['extracted_results'] = [{'provided': answer_submission.provided,
                                                                         'date': isoformat(answer_submission.date),
                                                                         'generated_text': GRTSubmission.query.filter_by(submission_id=answer_submission.id).first().text}
                                                                         for answer_submission 
                                                                         in query_results]
            log.debug(f'Extracted "{submission_type}" '
                      f'submissions: {answer_submissions[submission_type]["extracted_results"]}')
        response = {'success': True,
                                    'data': {'pending': answer_submissions[Pending]['extracted_results'],
                                             'correct': answer_submissions[Solves]['extracted_results'],
                                             'awarded': answer_submissions[Awarded]['extracted_results'],
                                             'incorrect': answer_submissions[Fails]['extracted_results']}}
        log.info(f'Showed user "{get_current_user().name}" '
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
