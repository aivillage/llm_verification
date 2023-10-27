"""Additional LLMV RESTful API routes that are added to CTFd."""
from logging import getLogger
import random
from uuid import uuid4

# Third-party imports.
from flask import Blueprint, jsonify, render_template, request, abort
from requests.exceptions import HTTPError
from werkzeug.exceptions import BadRequest

# CTFd imports.
from CTFd.models import Submissions, db
from CTFd.plugins import bypass_csrf_protection
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.modes import get_model
from CTFd.utils.user import get_current_user, is_admin
from CTFd.utils.scores import get_standings

# LLM Verification Plugin module imports.
from .llmv_models import LLMVSubmission, LlmAwards, LlmChallenge, LlmSolves, LLMVGeneration, LlmModels, models_not_submitted, LLMVChatPair
from .remote_llm import generate_text


log = getLogger(__name__)

def add_routes() -> Blueprint:
    """Add new GRT/LLMV routes to CTFd."""
    # Define HTML blueprints for the LLMV plugin.
    llm_verifications = Blueprint('llm_verifications', __name__, template_folder='templates')

    @llm_verifications.route('/admin/llm_verification', methods=['GET'])
    @admins_only
    def llm_verification_index():
        """Define a route for the LLMV plugin's index page."""
        standings = get_standings(admin=True)
        return render_template('index.html', standings=standings)

    @llm_verifications.route('/generate', methods=['POST'])
    @bypass_csrf_protection
    @authed_only
    def generate_for_challenge():
        """Add a route to CTFd for generating text from a prompt."""
        log.info(f'Received text generation request from user "{get_current_user().name}" '
                 f'for challenge ID "{request.json["challenge_id"]}"')
        
        challenge = LlmChallenge.query.filter_by(id=request.json['challenge_id']).first_or_404()

        if 'generation_id' in request.json:
            log.info("Found old generation id %s, using that", request.json['generation_id'])
            llmv_generation = LLMVGeneration.query.filter_by(id=request.json['generation_id']).first_or_404()
            if llmv_generation.status != "unsubmitted":
                log.error(f"Generation {request.json['generation_id']} has been submitted, status: {llmv_generation.status}, returning")
                response = {'success': False, 'data': {'text': "This challenge is complete.", "id": -1}}
                return jsonify(response)
            if llmv_generation.account_id != get_current_user().id:
                log.error(f"Generation {request.json['generation_id']} is not owned by user {get_current_user().id}, returning")
                response = {'success': False, 'data': {'text': "This challenge is complete.", "id": -1}}
                return jsonify(response)
            if llmv_generation.challenge_id != challenge.id:
                log.error(f"Generation {request.json['generation_id']} is not for challenge {challenge.id}, returning")
                response = {'success': False, 'data': {'text': "This challenge is complete.", "id": -1}}
                return jsonify(response)
            history = llmv_generation.pairs
            history = [h.json() for h in llmv_generation.pairs]
            log.info('Found history "%s"', history)
        else:
            left_over_model = models_not_submitted(user_id=get_current_user().id, challenge_id=challenge.id)
            if len(left_over_model) == 0:
                response = {'success': False, 'data': {'text': "This challenge is complete.", "id": -1}}
                return jsonify(response)
            # Add the generated text to the database.
            user_id = get_current_user().id
            team_id = get_current_user().team_id
            challenge_id = request.json['challenge_id']
            anon_name = random.choice(left_over_model)
            # Return a random model that isn't submitted by the user.
            model = LlmModels.query.filter_by(anon_name=anon_name).first()
            llmv_generation = LLMVGeneration(user_id=user_id,
                                        team_id=team_id,
                                        challenge_id=challenge_id,
                                        model_id=model.id,)
            db.session.add(llmv_generation)
            history = []
            log.info("No old generation id, starting new generation")

        preprompt = challenge.preprompt
        log.debug(f'Found pre-prompt "{preprompt}" '
                  f'for challenge {request.json["challenge_id"]} "{challenge.name}"')
        log.debug(f'User "{get_current_user().name}" '
                  f'submitted prompt: "{request.json["prompt"]}"')
        # Combine the pre-prompt and user-provided prompt with a space between them.
        prompt = request.json["prompt"]
        log.debug(f'pre-prompt {preprompt} and user-provided-prompt: "{prompt}"')
        idempotency_uuid = str(uuid4())
        try:
            model = LlmModels.query.filter_by(id=llmv_generation.model_id).first()
            generated_text = generate_text(idempotency_uuid, preprompt, prompt, model.model, history)
            generation_succeeded = True

        except HTTPError as error:
            log.error(f'Remote LLM experienced an error when generating text: {error}')
            # Send the error message from the HTTPError as the response to the user.
            response = {'success': False, 'data': {'text': "There was an error in the backend, try again?", "id": -1}}
            return jsonify(response)

        chatpair = LLMVChatPair(generation_id=llmv_generation.id, generation=generated_text, prompt=prompt, uuid=idempotency_uuid)
        db.session.add(chatpair)
        db.session.commit()
        generation_id = llmv_generation.id
        fragment = get_conversation(generation_id)
        response = {'success': generation_succeeded, 'data': {'text': generated_text, 'fragment': fragment, 'id': generation_id}}
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
        collected_submissions = []
        for status in ['pending', 'correct', 'awarded', 'incorrect']:
            generations = LLMVGeneration.query.add_columns(
                LlmModels.anon_name,
            ).filter_by(user_id=user_id, challenge_id=challenge_id, status=status).join(LlmModels).all()
            for generation, model_name in generations:
                collected_submissions.append({
                    'date': generation.date,
                    'status': status,
                    'model': model_name,
                    "fragment": get_conversation(generation.id),
                })

        left_over_model = models_not_submitted(user_id=user_id, challenge_id=challenge_id)
        

        response = {'success': True, 'data': {"submissions": collected_submissions, "models_left": left_over_model}}
        log.info(f'Showed user "{get_current_user().name}" '
                 f'their answer submissions for challenge "{challenge_id}"')
        return jsonify(response)
    
    @llm_verifications.route('/models_left/<challenge_id>', methods=['GET'])
    @authed_only
    def models_left(challenge_id):
        """Define a route for for showing users their answer submissions."""
        # Identify the user who would like to see their answer submissions.
        log.debug(f'User "{get_current_user().name}" '
                  f'requested their answer submissions for challenge "{challenge_id}"')
        # Query the database for the user's answer submissions for this challenge.
        user_id = get_current_user().id
        left_over_model = models_not_submitted(user_id=user_id, challenge_id=challenge_id)
        response = {'success': True, 'data': {"models_left": left_over_model}}
        return jsonify(response)

    @llm_verifications.route('/chat_limit/<challenge_id>', methods=['GET'])
    @authed_only
    def chat_limit(challenge_id):
        """Define a route for for showing users their answer submissions."""
        # Identify the user who would like to see their answer submissions.
        log.debug(f'User "{get_current_user().name}" '
                  f'requested their answer submissions for challenge "{challenge_id}"')
        # Query the database for the user's answer submissions for this challenge.
        challenge = LlmChallenge.query.filter_by(id=challenge_id).first_or_404()
        response = {'success': True, 'data': {"chat_limit": challenge.chat_limit}}
        return jsonify(response)
    
    #@llm_verifications.route('/admin/llm_submissions/pending', methods=['GET'])
    #@admins_only
    def render_pending_submissions():
        """Add an admin route for viewing answer submissions that haven't been reviewed."""
        filters = {'type': 'pending'}
        challenge_id = request.args.get('challenge_id', None, type=int)
        if challenge_id is not None:
            filters['challenge_id'] = challenge_id

        user_id = request.args.get('user_id', None, type=int)
        if user_id is not None:
            filters['user_id'] = user_id
        
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
                                                     LLMVGeneration.pairs).select_from(Submissions)
                                                                        .filter_by(**filters)
                                                                        .join(LlmChallenge, LlmChallenge.id == Submissions.challenge_id)
                                                                        .join(Model)
                                                                        .join(LLMVSubmission, LLMVSubmission.submission_id == Submissions.id)
                                                                        .join(LLMVGeneration, LLMVSubmission.generation_id == LLMVGeneration.id)
                                                                        .order_by(Submissions.date.desc())
                                                                        .slice(page_start, page_end)
                                                                        .all())
        log.info(f'Showed (admin) {len(submissions)} pending answer submissions')
        log.info(f'Submissions: {submissions}')
        return render_template('verify_submissions.html',
                                submissions=submissions,
                                page_count=page_count,
                                curr_page=curr_page)

    @llm_verifications.route('/llm_submissions/conversation/<generation_id>', methods=['GET'])
    @authed_only
    def get_conversation(generation_id):
        log.debug(f"Getting conversation for generation {generation_id}")
        generation = LLMVGeneration.query.filter_by(id=generation_id).first_or_404()
        if generation.account_id != get_current_user().id or not is_admin():
            abort(403, description="You are not authorized to view this page.") 
        
        conversation = LLMVChatPair.query.filter_by(generation_id=generation_id).order_by(LLMVChatPair.date).all()
        
        return render_template('conversation.html',conversation=conversation)



    def get_generations(request, pending_overide=False):
        """Add an admin route for viewing answer submissions that haven't been reviewed."""
        filters = {}
        status = request.args.get('status', None, type=str)
        if status is not None:
            filters['status'] = status

        if pending_overide:
            filters['status'] = 'pending'

        challenge_id = request.args.get('challenge_id', None, type=int)
        if challenge_id is not None:
            filters['challenge_id'] = challenge_id

        account_id = request.args.get('account_id', None, type=int)
        if account_id is not None:
            filters['account_id'] = account_id

        curr_page = abs(int(request.args.get('page', 1, type=int)))
        results_per_page = 50
        page_start = results_per_page * (curr_page - 1)
        page_end = results_per_page * (curr_page - 1) + results_per_page
        sub_count = LLMVGeneration.query.count()
        page_count = int(sub_count / results_per_page) + (sub_count % results_per_page > 0)
        Model = get_model()
        
        generations = (LLMVGeneration.query.add_columns(
                                                   LlmChallenge.name.label('challenge_name'),
                                                   LlmChallenge.description.label('challenge_description'),
                                                   Model.name.label('team_name')).select_from(LLMVGeneration)
                                                                                 .filter_by(**filters)
                                                                                 .join(LlmChallenge)
                                                                                 .join(Model)
                                                                                 .order_by(LLMVGeneration.date.desc())
                                                                                 .slice(page_start, page_end)
                                                                                 .all())
        log.debug(f'generations: {generations}')
        return generations, page_count, curr_page

    @llm_verifications.route('/admin/llm_submissions/generations', methods=['GET'])
    @admins_only
    def view_generations():
        generations, page_count, curr_page = get_generations(request)
        log.info(f'Showed (admin) all generations, {len(generations)} generations')
        return render_template('all_generations.html',
                               generations=generations,
                               page_count=page_count,
                               curr_page=curr_page)

    @llm_verifications.route('/admin/llm_submissions/pending', methods=['GET'])
    @admins_only
    def render_pending_submissions():
        """Add an admin route for viewing answer submissions that haven't been reviewed."""
        generations, page_count, curr_page = get_generations(request, pending_overide=True)
        log.info(f'Showed (admin) {len(generations)} pending answer generations')
        return render_template('verify_submissions.html',
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
    
    @llm_verifications.route('/admin/verify_submissions/<generation_id>/<status>', methods=['POST'])
    @admins_only
    def verify_submissions(generation_id, status):
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
                 f'marked answer submission "{generation_id}" '
                 f'as "{status}"')
        grt_submission = LLMVGeneration.query.filter_by(id=generation_id).first_or_404()
        log.debug(f'grt_submission: {grt_submission}')
        challenge = LlmChallenge.query.filter_by(id=grt_submission.challenge_id).first_or_404()
        log.debug(f'challenge: {challenge}')
        if status == 'solve':
            LLMVGeneration.query.filter_by(id=grt_submission.id).update({"points": challenge.value, "status": "correct"})
            db.session.commit()
        # Otherwise, if the answer submission was marked "incorrect"...
        elif status == 'fail':
            # Note that the answer submission failed its challenge in the (CTFd) Fails table.
            # Delete the award or solve from the LlmAwards or LlmSolves table.

            LLMVGeneration.query.filter_by(id=grt_submission.id).update({"points": 0, "status": "incorrect"})
            solve = LlmSolves.query.filter_by(generation_id=grt_submission.id).first()
            award = LlmAwards.query.filter_by(generation_id=grt_submission.id).first()
            if award:
                db.session.delete(award)
            if solve:
                db.session.delete(solve)

        # Otherwise, if the admin doesn't want to "solve," "award," or "fail" the answer submission...
        else:
            # ... then return a 400 status code and don't clear the answer submission from the CTFd "Submissions" table.
            raise BadRequest(f'Invalid argument "{status}" '
                             f'passed to parameter "status" for marking answer submission "{generation_id}"')
        # Delete the answer submission from CTFd's "Submissions" table, which also cascade-deletes the answer submission from the LLMVSubmissions table.
        db.session.commit()
        db.session.close()
        return jsonify({'success': True})

    return llm_verifications

    