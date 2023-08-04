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
from .llmv_models import LLMVSubmission, LLMVSolves, LlmChallenge, Pending, Awarded, LLMVGeneration
from .remote_llm import generate_text
from .utils import create_llmv_solve_entry, retrieve_submissions


log = getLogger(__name__)

def add_routes() -> Blueprint:
    """Add new GRT/LLMV routes to CTFd."""
    # Define HTML blueprints for the LLMV plugin.
    llm_verifications = Blueprint('llm_verifications', __name__, template_folder='templates')

    @llm_verifications.route('/admin/llm_verification', methods=['GET'])
    @admins_only
    def llm_verification_index():
        """Define a route for the LLMV plugin's index page."""
        return render_template('index.html')

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
            full_prompt, generated_text = generate_text(preprompt, prompt)
            generation_succeeded = True
        except HTTPError as error:
            log.error(f'Remote LLM experienced an error when generating text: {error}')
            # Send the error message from the HTTPError as the response to the user.
            generated_text = str(error)
            full_prompt = ""
            generation_succeeded = False

        user_id = get_current_user().id
        team_id = get_current_user().team_id
        challenge_id = request.json['challenge_id']
        text = generated_text
        grt_generation = LLMVGeneration(user_id=user_id,
                                       team_id=team_id,
                                       challenge_id=challenge_id,
                                       text=text,
                                       prompt=prompt,
                                       full_prompt=full_prompt,)
        db.session.add(grt_generation)
        db.session.commit()
        grt_generation_id = grt_generation.id

        response = {'success': generation_succeeded, 'data': {'text': generated_text, 'id': grt_generation_id}}
        log.info(f'Generated text for user "{get_current_user().name}" '
                 f'for challenge "{challenge.name}" with id {grt_generation_id}')
        
        log.debug(f"Total number of generated texts: {LLMVGeneration.query.count()}")

        return jsonify(response)

    @llm_verifications.route('/submissions/<challenge_id>', methods=['GET'])
    @authed_only
    def submissions_for_challenge(challenge_id):
        """Define a route for for showing users their answer submissions."""
        # Identify the user who would like to see their answer submissions.
        log.debug(f'User "{get_current_user().name}" '
                  f'requested their answer submissions for challenge "{challenge_id}"')
        # Query the database for the user's answer submissions for this challenge.
        user_id = get_current_user().id
        collected_submissions = {type_label: retrieve_submissions(submission_type=submission_type,
                                                                  challenge_id=challenge_id,
                                                                  user_id=user_id)
                                 for type_label, submission_type in (('pending', Pending),
                                                                     ('correct', Solves),
                                                                     ('awarded', Awarded),
                                                                     ('incorrect', Fails))}
        response = {'success': True, 'data': collected_submissions}
        log.info(f'Showed user "{get_current_user().name}" '
                 f'their answer submissions for challenge "{challenge_id}"')
        return jsonify(response)
    
    @llm_verifications.route('/admin/llm_submissions/pending', methods=['GET'])
    @admins_only
    def render_pending_submissions(challenge_id=None):
        """Add an admin route for viewing answer submissions that haven't been reviewed."""
        challenge_id = request.args.get('challenge_id', None, type=int)
        if challenge_id is None:
            filters = {'type': 'pending'}
        else:
            filters = {'type': 'pending', 'challenge_id': challenge_id}
        
        log.debug(f"Total number of generated texts, submitted but not graded: {LLMVGeneration.query.filter_by(status='pending').count()}")
        log.debug(f"Total number of submissions, submitted but not graded: {LLMVSubmission.query.count()}")
        log.debug(f"Total number of submissions: {Submissions.query.count()}")
        log.debug(f"Total number of submissions that are pending: {Submissions.query.filter_by(**filters).count()}")


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
                                                     LlmChallenge.name.label('challenge_name'),
                                                     Model.name.label('team_name'),
                                                     LLMVGeneration.prompt,
                                                     LLMVGeneration.text).select_from(Submissions)
                                                                        .filter_by(**filters)
                                                                        .join(LlmChallenge, LlmChallenge.id == Submissions.challenge_id)
                                                                        .join(Model)
                                                                        .join(LLMVSubmission, LLMVSubmission.submission_id == Submissions.id)
                                                                        .join(LLMVGeneration, LLMVSubmission.generation_id == LLMVGeneration.id)
                                                                        .order_by(Submissions.date.desc())
                                                                        .slice(page_start, page_end)
                                                                        .all())
        log.info(f'Showed (admin) {len(submissions)} pending answer submissions')
        return render_template('verify_submissions.html',
                                submissions=submissions,
                                page_count=page_count,
                                curr_page=curr_page)

    
    @llm_verifications.route('/admin/llm_submissions/solved', methods=['GET'])
    @admins_only
    def render_solved_submissions(challenge_id=None):
        """Add an admin route for viewing answer submissions that have been marked as correct."""
        challenge_id = request.args.get('challenge_id', None, type=int)
        if challenge_id is None:
            filters = {'success': True}
        else:
            filters = {'success': True, 'challenge_id': challenge_id}
        curr_page = abs(int(request.args.get('page', 1, type=int)))
        results_per_page = 50
        page_start = results_per_page * (curr_page - 1)
        page_end = results_per_page * (curr_page - 1) + results_per_page
        sub_count = LLMVSolves.query.filter_by(**filters).count()
        page_count = int(sub_count / results_per_page) + (sub_count % results_per_page > 0)
        Model = get_model()
        submissions = (LLMVSolves.query.add_columns(LLMVSolves.id,
                                                   LLMVSolves.challenge_id,
                                                   LLMVSolves.prompt,
                                                   LLMVSolves.account_id,
                                                   LLMVSolves.text,
                                                   LLMVSolves.date,
                                                   LlmChallenge.name.label('challenge_name'),
                                                   LlmChallenge.description.label('challenge_description'),
                                                   Model.name.label('team_name')).select_from(LLMVSolves)
                                                                                 .filter_by(**filters)
                                                                                 .join(LlmChallenge)
                                                                                 .join(Model)
                                                                                 .order_by(LLMVSolves.date.desc())
                                                                                 .slice(page_start, page_end)
                                                                                 .all())
        log.info(f'Showed (admin) solved answer submissions')
        return render_template('solved_submissions.html',
                               submissions=submissions,
                               page_count=page_count,
                               curr_page=curr_page)

    @llm_verifications.route('/admin/llm_submissions/all_generations', methods=['GET'])
    @admins_only
    def view_generations():
        curr_page = abs(int(request.args.get('page', 1, type=int)))
        results_per_page = 50
        page_start = results_per_page * (curr_page - 1)
        page_end = results_per_page * (curr_page - 1) + results_per_page
        sub_count = LLMVGeneration.query.count()
        page_count = int(sub_count / results_per_page) + (sub_count % results_per_page > 0)
        Model = get_model()
        challenge_id = request.args.get('challenge_id', None, type=int)
        if challenge_id is None:
            filters = {}
        else:
            filters = {'challenge_id': challenge_id}
        generations = (LLMVGeneration.query.add_columns(LLMVGeneration.id,
                                                   LLMVGeneration.challenge_id,
                                                   LLMVGeneration.prompt,
                                                   LLMVGeneration.account_id,
                                                   LLMVGeneration.text,
                                                   LLMVGeneration.status,
                                                   LLMVGeneration.points,
                                                   LLMVGeneration.date,
                                                   LlmChallenge.name.label('challenge_name'),
                                                   LlmChallenge.description.label('challenge_description'),
                                                   Model.name.label('team_name')).select_from(LLMVGeneration)
                                                                                 .filter_by(**filters)
                                                                                 .join(LlmChallenge)
                                                                                 .join(Model)
                                                                                 .order_by(LLMVGeneration.date.desc())
                                                                                 .slice(page_start, page_end)
                                                                                 .all())
        
        log.info(f'Showed (admin) all generations, {len(generations)} generations')
        return render_template('all_generations.html',
                               generations=generations,
                               page_count=page_count,
                               curr_page=curr_page)

    
    @llm_verifications.route('/admin/llm_submissions/challenges', methods=['GET'])
    @admins_only
    def view_challenges():
        """Add an admin route for viewing answer submissions that have been marked as correct."""
        curr_page = abs(int(request.args.get('page', 1, type=int)))
        results_per_page = 50
        page_start = results_per_page * (curr_page - 1)
        page_end = results_per_page * (curr_page - 1) + results_per_page
        sub_count = LlmChallenge.query.count()
        page_count = int(sub_count / results_per_page) + (sub_count % results_per_page > 0)
        challenges = (LlmChallenge.query.add_columns(LlmChallenge.id,
                                                   LlmChallenge.name,
                                                   LlmChallenge.description,
                                                   LlmChallenge.value,
                                                   LlmChallenge.preprompt,
                                                   LlmChallenge.category).select_from(LlmChallenge)
                                                                                 .order_by(LlmChallenge.id.desc())
                                                                                 .slice(page_start, page_end)
                                                                                 .all())
        log.info(f'Showed (admin) all challenges, {len(challenges)} challenges')
        return render_template('all_challenges.html',
                               challenges=challenges,
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
        # Retrieve the answer submission from the "LLMVSubmissions" table.
        log.debug(f'ctfd_submission: {ctfd_submission}')
        grt_submission = LLMVSubmission.query.filter_by(submission_id=submission_id).first_or_404()
        log.debug(f'grt_submission: {grt_submission}')
        challenge = LlmChallenge.query.filter_by(id=grt_submission.challenge_id).first_or_404()
        log.debug(f'challenge: {challenge}')
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
            # Add the user's (correct) answer submission solution to the LLMVSolves table.
            grt_solve = create_llmv_solve_entry(solve_status=True,
                                               ctfd_submission=ctfd_submission,
                                               grt_submission=grt_submission)
            db.session.add(grt_solve)
            LLMVGeneration.query.filter_by(id=grt_submission.generation_id).update({"points": challenge.value, "status": "success"})
        
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
            # Add the user's (correct) answer submission solution to the LLMVSolves table.
            grt_solve = create_llmv_solve_entry(solve_status=True,
                                               ctfd_submission=ctfd_submission,
                                               grt_submission=grt_submission)
            db.session.add(grt_solve)

            LLMVGeneration.query.filter_by(id=grt_submission.generation_id).update(
                {"points": request.args.get('value', 0), "status": "success"},
            )

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
            # Add the user's (incorrect) answer submission solution to the LLMVSolves table.
            grt_solve = create_llmv_solve_entry(solve_status=False,
                                               ctfd_submission=ctfd_submission,
                                               grt_submission=grt_submission)
            db.session.add(grt_solve)
            LLMVGeneration.query.filter_by(id=grt_submission.generation_id).update({"points": 0, "status": "fail"})

        # Otherwise, if the admin doesn't want to "solve," "award," or "fail" the answer submission...
        else:
            # ... then return a 400 status code and don't clear the answer submission from the CTFd "Submissions" table.
            raise BadRequest(f'Invalid argument "{status}" '
                             f'passed to parameter "status" for marking answer submission "{submission_id}"')
        # Delete the answer submission from CTFd's "Submissions" table, which also cascade-deletes the answer submission from the LLMVSubmissions table.
        db.session.delete(ctfd_submission)
        log.debug(f'Deleted user "{ctfd_submission.user_id}"\'s '
                  f'answer submission "{submission_id}" '
                  f'to CTFd\'s Submissions table')
        db.session.commit()
        db.session.close()
        return jsonify({'success': True})

    return llm_verifications

    