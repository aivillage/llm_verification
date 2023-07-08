# Standard library imports.
import datetime
from logging import getLogger

# Third-party imports.
from flask import Blueprint, jsonify, render_template, request
from requests import post
from requests.exceptions import HTTPError
from sqlalchemy.ext.hybrid import hybrid_property

# CTFd imports.
from CTFd.models import Awards, Challenges, Fails, Solves, Submissions, db
from CTFd.plugins import bypass_csrf_protection, register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES, BaseChallenge
from CTFd.plugins.migrations import upgrade as ctfd_migrations
from CTFd.utils import get_config
from CTFd.utils.dates import isoformat
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.modes import USERS_MODE, get_model
from CTFd.utils.user import get_current_user, get_ip

# LLM Verification Plugin module imports.
from .llmv_logger import initialize_grtctfd_loggers
from .config_manager import load_llmv_config


log = getLogger(__name__)

def load(app):
    """Load plugin config from TOML file and register plugin assets."""
    print('Loading LLM Verification Plugin')
    # Get the logger for the LLM Verification plugin.
    log = initialize_grtctfd_loggers(module_name=__name__)
    # Perform database migrations (if necessary).
    ctfd_migrations()
    log.debug('Performed CTFd database migrations')
    CHALLENGE_CLASSES['llm_verification'] = LlmSubmissionChallenge
    register_plugin_assets_directory(app, base_path='/plugins/llm_verification/assets/')
    log.debug('Registered LLMV plugin assets directory with CTFd')
    llm_verifications = Blueprint('llm_verifications', __name__, template_folder='templates')
    log.debug('Registered LLMV blueprints with CTFd')
    # Open the llm_config.toml file and get the host and port
    log.info('Loaded LLM Verification Plugin "LLMV"')

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

    app.register_blueprint(llm_verifications)

class LlmChallenge(Challenges):
    """SQLAlchemy Table model for LLM Challenges."""
    __mapper_args__ = {'polymorphic_identity': 'llm_verification'}
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer,
                        db.ForeignKey('challenges.id', ondelete='CASCADE'),
                        primary_key=True)
    preprompt = db.Column(db.Text)
    llm = db.Column(db.Text)

    def __init__(self, *args, **kwargs):
        super(LlmChallenge, self).__init__(**kwargs)

    @property
    def html(self):
        from CTFd.utils.config.pages import build_markdown
        from CTFd.utils.helpers import markup
        return markup(build_markdown(self.description))


class Pending(Submissions):
    __mapper_args__ = {'polymorphic_identity': 'pending'}

class Awarded(Submissions):
    __mapper_args__ = {'polymorphic_identity': 'awarded'}

class GRTSubmission(db.Model):
    """GRT CTFd SQLAlchemy table for answer submissions."""
    __tablename__ = 'grt_submissions'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id', ondelete='CASCADE'))
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id', ondelete='CASCADE'))
    text = db.Column(db.Text)
    prompt = db.Column(db.Text)

class GRTSolves(db.Model):
    """GRT CTFd SQLAlchemy table for solve attempts."""
    __tablename__ = 'grt_solves'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    success = db.Column(db.Boolean)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id', ondelete='CASCADE'))
    text = db.Column(db.Text)
    prompt = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    @hybrid_property
    def account_id(self):
        from CTFd.utils import get_config

        user_mode = get_config('user_mode')
        if user_mode == 'teams':
            return self.team_id
        elif user_mode == 'users':
            return self.user_id


class LlmSubmissionChallenge(BaseChallenge):
    """Customized CTFd challenge type for LLM submissions."""
    __version__ = '1.1.1'
    id = 'llm_verification'  # Unique identifier used to register challenges
    name = 'llm_verification'  # Name of a challenge type
    # Handlebars templates used for each aspect of challenge editing & viewing
    templates = {'create': '/plugins/llm_verification/assets/create.html',
                                 'update': '/plugins/llm_verification/assets/update.html',
                                 'view': '/plugins/llm_verification/assets/view.html',}
    # Scripts that are loaded when a template is loaded
    scripts = {'create': '/plugins/llm_verification/assets/create.js',
                               'update': '/plugins/llm_verification/assets/update.js',
                               'view': '/plugins/llm_verification/assets/view.js',}
    # Route at which files are accessible. This must be registered using register_plugin_assets_directory()
    route = '/plugins/llm_verification/assets/'
    # Blueprint used to access the static_folder directory.
    blueprint = Blueprint('llm_verification', __name__, template_folder='templates', static_folder='assets',)
    challenge_model = LlmChallenge

    @classmethod
    def create(cls, request):
        """Process the challenge creation request.

        Arguments:
            request: The Flask request object.

        Returns:
            Challenge: The newly created challenge.
        """
        data = request.form or request.get_json()
        challenge = cls.challenge_model(**data)
        db.session.add(challenge)
        db.session.commit()
        log.info(f'Created challenge: {data}')
        return challenge

    @staticmethod
    def attempt(challenge, request):
        """This method is not used as llm submissions are not solved with the compare() method.

        Arguments:
            challenge: The Challenge object from the database
            request: The request the user submitted

        Returns:
            tuple (bool, str):  This will always be `False` and `'Submission under review'` because
                llm submissions need manual review.
        """
        log.info('Rejected "attempt" because manual verification is needed')
        return False, 'Submission under review'

    @staticmethod
    def solve(user, team, challenge, request):
        """ This method is not used as llm submission challenges are not solved with flags.

        Arguments:
            team: The Team object from the database
            challenge: The Challenge object from the database
            request: The request the user submitted

        Returns:
            `None`
        """
        log.info('Rejected "solve" because manual verification is needed')
        return None

    @staticmethod
    def fail(user, team, challenge, request):
        """Mark an an attempt as "pending" by inserting "Pending" into the database.

        Arguments:
            team: The Team object from the database
            challenge: The Challenge object from the database
            request: The request the user submitted

        Returns:
            `None`
        """
        data = request.form or request.get_json()
        submission = data['submission']
        pending = Pending(user_id=user.id,
                          team_id=team.id if team else None,
                          challenge_id=challenge.id,
                          ip=get_ip(request),
                          provided=submission,)
        db.session.add(pending)
        db.session.commit()
        grt = GRTSubmission(submission_id=pending.id,
                            text=data['text'],
                            prompt=data['prompt'],
                            challenge_id=challenge.id,)
        db.session.add(grt)
        db.session.commit()
        log.info(f'Fail: marked attempt as pending: {submission}')
        return None

def generate_text(prompt):
    """Generate text from a prompt using the EleutherAI GPT-NeoX-20B model.

    Arguments:
        prompt: The prompt to generate text from.

    Raises:
        ValueError: If the Vanilla Neox API key is not set.
        HTTPError: If the EleutherAI API returns a non-200 HTTP status code.

    Returns:
        str: Text generated by the prompt.
    """
    log.info(f'Received text generation request for prompt "{prompt}"')
    # Load the Vanilla Neox API key from the config file.
    llmv_config = load_llmv_config()
    neox_token = llmv_config['vanilla_neox_api_key']
    if neox_token == 'UNSET':
        raise ValueError('Vanilla Neox API key is not set')
    response = post(url='https://api-inference.huggingface.co/models/EleutherAI/gpt-neox-20b',
                              headers={'Authorization': f'Bearer {neox_token}'},
                              json={'inputs': prompt})
    log.debug(f'Received {response.status_code} response from EleutherAI API')
    # If it's a successful HTTP status code, then...
    if response.status_code == 200:
        json_response = response.json()
        log.debug(f'Response: {json_response}')
        generated_text = json_response[0]['generated_text']
        # Remove newlines from the generated text.
        oneline_generation = generated_text.replace('\n', ' ')
        log.info(f'Received generated text from remote API: {oneline_generation}...')
        response = oneline_generation
    elif 400 <= response.status_code <= 599:
        # ... raise an error.
        raise HTTPError(f'EleutherAI API returned error status code {response.status_code}: '
                        f'Response: {response.json()}')
    # ... Otherwise, if it's an unrecognized HTTP status code, then...
    else:
        raise HTTPError(f'EleutherAI API returned unrecognized status code {response.status_code}: '
                        f'Response: {response.json()}')
        response = 'Error generating text.'
    log.info(f'Completed text generation for prompt "{prompt}"')
    return response

