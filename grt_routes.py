"""Additional LLMV RESTful API routes that are added to CTFd."""
from logging import getLogger

# Third-party imports.
from flask import Blueprint, jsonify, render_template, request
from requests.exceptions import HTTPError
from werkzeug.exceptions import BadRequest

# CTFd imports.
from CTFd.models import Awards, Challenges, Fails, Solves, Submissions, db
from CTFd.plugins import bypass_csrf_protection
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.modes import get_model
from CTFd.utils.user import get_current_user

# LLM Verification Plugin module imports.
from .grt_models import GRTSubmission, GRTSolves, LlmChallenge, Pending, Awarded
from .remote_llm import generate_text
from .utils import create_grt_solve_entry, retrieve_submissions


log = getLogger(__name__)

def add_routes() -> Blueprint:
    """Add new GRT/LLMV routes to CTFd."""
    # Define HTML blueprints for the LLMV plugin.
    llm_verifications = Blueprint('llm_verifications', __name__, template_folder='templates')

    @llm_verifications.route('/generate', methods=['POST'])
    @bypass_csrf_protection
    @authed_only
    def generate_for_challenge():
        """Add a route to CTFd for generating text from a prompt."""
        log.info(f'Received text generation request from user "{get_current_user().name}" '
                 f'for challenge ID "{request.json["challenge_id"]}"')
        challenge = LlmChallenge.query.filter_by(id=request.json['challenge_id']).first_or_404()
        preprompt = challenge.preprompt
        log.debug(f'Found pre-prompt "{preprompt}" '
                  f'for challenge {request.json["challenge_id"]} "{challenge.name}"')
        log.debug(f'User "{get_current_user().name}" '
                  f'submitted prompt: "{request.json["prompt"]}"')
        # Combine the pre-prompt and user-provided prompt with a space between them.
        prompt = request.json["prompt"]
        log.debug(f'pre-prompt {preprompt} and user-provided-prompt: "{prompt}"')
        try:
            generated_text = generate_text(preprompt, prompt)
            generation_succeeded = True
        except HTTPError as error:
            log.error(f'Remote LLM experienced an error when generating text: {error}')
            # Send the error message from the HTTPError as the response to the user.
            generated_text = str(error)
            generation_succeeded = False
        log.error(f'Preprompt setting: {challenge.remove_preprompt}')
        # If the pre-prompt needs to be removed from the generated text...
        if challenge.remove_preprompt and preprompt in generated_text:
            # ... then remove the pre-prompt from the generated text.
            generated_text = generated_text.replace(preprompt, '')
            log.info(f'Removed pre-prompt "{preprompt}" from generated text')
        response = {'success': generation_succeeded, 'data': {'text': generated_text}}
        log.info(f'Generated text for user "{get_current_user().name}" '
                 f'for challenge "{challenge.name}"')
        return jsonify(response)

    @llm_verifications.route('/submissions/<challenge_id>', methods=['GET'])
    @authed_only
    def submissions_for_challenge(challenge_id):
        """Define a route for for showing users their answer submissions."""
        # Identify the user who would like to see their answer submissions.
        log.debug(f'User "{get_current_user().name}" '
                  f'requested their answer submissions for challenge "{challenge_id}"')
        # Query the database for the user's answer submissions for this challenge.
        collected_submissions = {type_label: retrieve_submissions(submission_type=submission_type,
                                                                  challenge_id=challenge_id)
                                 for type_label, submission_type in (('pending', Pending),
                                                                     ('correct', Solves),
                                                                     ('awarded', Awarded),
                                                                     ('incorrect', Fails))}
        response = {'success': True, 'data': collected_submissions}
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
        """Add a route for admins to mark answer attempts as correct or incorrect.

        Arguments:
            submission_id (int): The ID of the answer submission to mark.
            status (str): The status to mark the answer submission with.
                Choose from `solve`, `fail`, or `incorrect`.

        Raises:
            BadRequest: If the status is not `solve`, `fail`, or `incorrect`, which translates
                to a 400 status code.

        Returns:
            JSON(dict): {'success': True}
        """
        log.info(f'Admin "{get_current_user().name}" '
                 f'marked answer submission "{submission_id}" '
                 f'as "{status}"')
        # Retrieve the answer submission from the (CTFd) "Submissions" table.
        ctfd_submission = Submissions.query.filter_by(id=submission_id).first_or_404()
        # Retrieve the answer submission from the "GRTSubmissions" table.
        grt_submission = GRTSubmission.query.filter_by(id=submission_id).first_or_404()
        if status == 'solve':
            # Note that the answer submission solved its challenge in the Solves table.
            solve = Solves(user_id=ctfd_submission.user_id,
                           team_id=ctfd_submission.team_id,
                           challenge_id=ctfd_submission.challenge_id,
                           ip=ctfd_submission.ip,
                           provided=ctfd_submission.provided,
                           date=ctfd_submission.date)
            db.session.add(solve)
            log.debug(f'Added user "{ctfd_submission.user_id}"\'s '
                      f'answer submission "{submission_id}" '
                      f'to the Solves table')
            # Remove the user's other "pending" answer submissions for this challenge from the (CTfd) "Submissions" table.
            Submissions.query.filter(Submissions.challenge_id == ctfd_submission.challenge_id,
                                     Submissions.team_id == ctfd_submission.team_id,
                                     Submissions.user_id == ctfd_submission.user_id,
                                     Submissions.type == 'pending').delete()
            log.debug(f'Removed user "{ctfd_submission.user_id}"\'s '
                      f'remaining pending answer submissions for challenge "{ctfd_submission.challenge_id}"')
            # Add the user's (correct) answer submission solution to the GRTSolves table.
            grt_solve = create_grt_solve_entry(solve_status=True,
                                               ctfd_submission=ctfd_submission,
                                               grt_submission=grt_submission)
            db.session.add(grt_solve)
        elif status == 'award':
            # Note that the submission solved its challenge in the (GRT) Awarded table.
            awarded = Awarded(user_id=ctfd_submission.user_id,
                              team_id=ctfd_submission.team_id,
                              challenge_id=ctfd_submission.challenge_id,
                              ip=ctfd_submission.ip,
                              provided=ctfd_submission.provided)
            db.session.add(awarded)
            log.debug(f'Added user "{ctfd_submission.user_id}"\'s '
                      f'answer submission "{submission_id}" '
                      f'to GRT\'s Awarded table')
            # Note that the submission solved its challenge in the (CTFd) Awards table and assign the grader's points to the user.
            award = Awards(user_id=ctfd_submission.user_id,
                           team_id=ctfd_submission.team_id,
                           name='Submission',
                           description='Correct Submission for {name}'.format(name=ctfd_submission.challenge.name),
                           value=request.args.get('value', 0),
                           category=ctfd_submission.challenge.category)
            db.session.add(award)
            log.debug(f'Added user "{ctfd_submission.user_id}"\'s '
                      f'answer submission "{submission_id}" '
                      f'to CTFd\'s Awards table')
            # Add the user's (correct) answer submission solution to the GRTSolves table.
            grt_solve = create_grt_solve_entry(solve_status=True,
                                               ctfd_submission=ctfd_submission,
                                               grt_submission=grt_submission)
            db.session.add(grt_solve)
        # Otherwise, if the answer submission was marked "incorrect"...
        elif status == 'fail':
            # Note that the answer submission failed its challenge in the (CTFd) Fails table.
            wrong = Fails(user_id=ctfd_submission.user_id,
                          team_id=ctfd_submission.team_id,
                          challenge_id=ctfd_submission.challenge_id,
                          ip=ctfd_submission.ip,
                          provided=ctfd_submission.provided,
                          date=ctfd_submission.date)
            db.session.add(wrong)
            log.debug(f'Added user "{ctfd_submission.user_id}"\'s '
                      f'answer submission "{submission_id}" '
                      f'to CTFd\'s Fails table')
            # Add the user's (incorrect) answer submission solution to the GRTSolves table.
            grt_solve = create_grt_solve_entry(solve_status=False,
                                               ctfd_submission=ctfd_submission,
                                               grt_submission=grt_submission)
            db.session.add(grt_solve)
        # Otherwise, if the admin doesn't want to "solve," "award," or "fail" the answer submission...
        else:
            # ... then return a 400 status code and don't clear the answer submission from the CTFd "Submissions" table.
            raise BadRequest(f'Invalid argument "{status}" '
                             f'passed to parameter "status" for marking answer submission "{submission_id}"')
        # Delete the answer submission from CTFd's "Submissions" table, which also cascade-deletes the answer submission from the GRTSubmissions table.
        db.session.delete(ctfd_submission)
        log.debug(f'Deleted user "{ctfd_submission.user_id}"\'s '
                  f'answer submission "{submission_id}" '
                  f'to CTFd\'s Submissions table')
        db.session.commit()
        db.session.close()
        return jsonify({'success': True})

    return llm_verifications
