"""Modified versions of CTFd's database models."""
# Standard library imports.
import datetime
from logging import getLogger

# Third-party imports.
from flask import Blueprint
from sqlalchemy.ext.hybrid import hybrid_property

# CTFd imports.
from CTFd.models import Challenges, Submissions, db
from CTFd.plugins.challenges import BaseChallenge
from CTFd.utils.user import get_ip


log = getLogger(__name__)

class LLMVGeneration(db.Model):
    """LLMV CTFd SQLAlchemy table for answer generation."""
    __tablename__ = 'llmv_generation'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id', ondelete='CASCADE'))
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id', ondelete='CASCADE'))
    model_id = db.Column(db.Integer, db.ForeignKey('llmv_models.id', ondelete='CASCADE'))

    text = db.Column(db.Text)
    prompt = db.Column(db.Text)
    points = db.Column(db.Integer, default=0)
    status = db.Column(db.String(80), default="unsubmitted")
    report = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    @hybrid_property
    def account_id(self):
        from CTFd.utils import get_config
        user_mode = get_config('user_mode')
        if user_mode == 'teams':
            return self.team_id
        elif user_mode == 'users':
            return self.user_id

class LLMVSubmission(db.Model):
    """LLMV CTFd SQLAlchemy table for answer submissions."""
    __tablename__ = 'llmv_submissions'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    generation_id = db.Column(db.Integer, db.ForeignKey('llmv_generation.id', ondelete='CASCADE'))
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id', ondelete='CASCADE'))
    text = db.Column(db.Text)
    prompt = db.Column(db.Text)

class LLMVSolves(db.Model):
    """LLMV CTFd SQLAlchemy table for solve attempts."""
    __tablename__ = 'llmv_solves'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    success = db.Column(db.Boolean)
    generation_id = db.Column(db.Integer, db.ForeignKey('llmv_generation.id', ondelete='CASCADE'))

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

class LlmChallenge(Challenges):
    """SQLAlchemy Table model for LLM Challenges."""
    __mapper_args__ = {'polymorphic_identity': 'llm_verification'}
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer,
                   db.ForeignKey('challenges.id', ondelete='CASCADE'),
                   primary_key=True)
    preprompt = db.Column(db.Text)

    def __init__(self, *args, **kwargs):
        super(LlmChallenge, self).__init__(**kwargs)

    @property
    def html(self):
        from CTFd.utils.config.pages import build_markdown
        from CTFd.utils.helpers import markup
        return markup(build_markdown(self.description))
    
class LlmModels(db.Model):
    """SQLAlchemy Table model for LLM Models."""
    __tablename__ = 'llm_models'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    anon_name = db.Column(db.String(80))
    model = db.Column(db.String(80))

class Pending(Submissions):
    __mapper_args__ = {'polymorphic_identity': 'pending'}

class Triaged(Submissions):
    __mapper_args__ = {'polymorphic_identity': 'triaged'}

class Awarded(Submissions):
    __mapper_args__ = {'polymorphic_identity': 'awarded'}

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
        """Process a challenge creation request submitted by an administrator.

        Arguments:
            request: The Flask request object.

        Returns:
            Challenge: The newly created challenge.
        """
        data = request.form or request.get_json()
        # Make LLM challenges visible to users by default.
        data['state'] = 'visible'
        challenge = cls.challenge_model(**data)
        db.session.add(challenge)
        db.session.commit()
        log.info(f'Created challenge: {data}')
        return challenge

    @staticmethod
    def attempt(challenge, request):
        """Filler method to satisfy the BaseChallenge interface.

        Normally, this would be used to check a user's submitted answer against the challenge's
        correct answer "flag" with the `compare()` method. However, Llm submissions are not solved
        with flags.

        Arguments:
            challenge: The Challenge object from the database
            request: The request the user submitted

        Returns:
            tuple (bool, str):  This will always be `False` and `'Submission under review'` because
                llm submissions need manual review.
        """
        log.info('Attempt: Rejected "attempt" because manual verification is needed')
        return False, 'Submission under review'

    @staticmethod
    def solve(user, team, challenge, request):
        """Filler method to satisfy BaseChallenge interface.

        This method is not used as LLM answer submissions are not solved with flags.

        Arguments:
            team: The Team object from the database
            challenge: The Challenge object from the database
            request: The request the user submitted

        Returns:
            `None`
        """
        log.info('Solve: Rejected "solve" because manual verification is needed')
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
        submission = data['submission'].strip()
        log.info(f'Old submissions: {LLMVSubmission.query.filter_by(generation_id=int(submission)).count()}')
        if 0 < LLMVSubmission.query.filter_by(generation_id=int(submission)).count():
            log.info('Submission already exists')
            return None
        log.info(data)
        generation = LLMVGeneration.query.filter_by(id=int(submission)).update({"status": "submitted"})

        generation = LLMVGeneration.query.add_columns(
            LLMVGeneration.id,
            LLMVGeneration.text,
            LLMVGeneration.prompt,
            LLMVGeneration.challenge_id,
            ).filter_by(id=int(submission)).first_or_404()
        db.session.commit()
        assert generation.challenge_id == challenge.id

        text = generation.text
        prompt = generation.prompt
        log.info(f'Have generation with prompt and text: {prompt} {text}')

        pending = Pending(user_id=user.id,
                          team_id=team.id if team else None,
                          challenge_id=challenge.id,
                          ip=get_ip(request),
                          provided=submission,)
        db.session.add(pending)
        db.session.commit()
        LLMV = LLMVSubmission(submission_id=pending.id,
                            text=text,
                            prompt=prompt,
                            challenge_id=challenge.id,
                            generation_id=generation.id,)
        db.session.add(LLMV)
        db.session.commit()
        log.info(f'Fail: marked attempt as pending: {submission}')