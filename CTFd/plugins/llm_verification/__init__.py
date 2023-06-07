from dataclasses import dataclass
from flask import Blueprint, jsonify, render_template, request

import os, json, traceback, requests

import toml
from .remote_llm.client import ClientLLM
from grpclib.client import Channel
import datetime
from sqlalchemy.ext.hybrid import hybrid_property

from CTFd.models import Awards, Challenges, Fails, Solves, Submissions, db
from CTFd.plugins import bypass_csrf_protection, register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES, BaseChallenge
from CTFd.plugins.migrations import upgrade
from CTFd.utils import get_config
from CTFd.utils.dates import isoformat
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.modes import USERS_MODE, get_model
from CTFd.utils.user import get_current_user, get_ip

class LlmChallenge(Challenges):
    """SQLAlchemy Table model for LLM Challenges."""
    __mapper_args__ = {"polymorphic_identity": "llm_verification"}
    __table_args__ = {'extend_existing': True} 

    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
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
    __mapper_args__ = {"polymorphic_identity": "pending"}

class Awarded(Submissions):
    __mapper_args__ = {"polymorphic_identity": "awarded"}

class GRTSubmission(db.Model):
    """GRT CTFd SQLAlchemy table for answer submissions."""
    __tablename__ = "grt_submissions"
    __table_args__ = {'extend_existing': True} 
    
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("submissions.id", ondelete="CASCADE"))
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"))
    text = db.Column(db.Text)
    prompt = db.Column(db.Text)

class GRTSolves(db.Model):
    """GRT CTFd SQLAlchemy table for solve attempts."""
    __tablename__ = "grt_solves"
    __table_args__ = {'extend_existing': True} 
    
    id = db.Column(db.Integer, primary_key=True)
    success = db.Column(db.Boolean)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"))
    text = db.Column(db.Text)
    prompt = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    @hybrid_property
    def account_id(self):
        from CTFd.utils import get_config

        user_mode = get_config("user_mode")
        if user_mode == "teams":
            return self.team_id
        elif user_mode == "users":
            return self.user_id


class LlmSubmissionChallenge(BaseChallenge):
    """Customized CTFd challenge type for LLM submissions."""
    __version__ = "1.1.1"
    id = "llm_verification"  # Unique identifier used to register challenges
    name = "llm_verification"  # Name of a challenge type
    templates = {  # Handlebars templates used for each aspect of challenge editing & viewing
        "create": "/plugins/llm_verification/assets/create.html",
        "update": "/plugins/llm_verification/assets/update.html",
        "view": "/plugins/llm_verification/assets/view.html",
    }
    scripts = {  # Scripts that are loaded when a template is loaded
        "create": "/plugins/llm_verification/assets/create.js",
        "update": "/plugins/llm_verification/assets/update.js",
        "view": "/plugins/llm_verification/assets/view.js",
    }
    # Route at which files are accessible. This must be registered using register_plugin_assets_directory()
    route = "/plugins/llm_verification/assets/"
    # Blueprint used to access the static_folder directory.
    blueprint = Blueprint(
        "llm_verification",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )
    challenge_model = LlmChallenge

    @classmethod
    def create(cls, request):
        """
        This method is used to process the challenge creation request.

        :param request:
        :return:
        """
        data = request.form or request.get_json()    

        challenge = cls.challenge_model(**data)

        db.session.add(challenge)
        db.session.commit()

        return challenge
    
    @staticmethod
    def attempt(challenge, request):
        """
        This method is not used as llm submissions are not solved with the compare() method.

        :param challenge: The Challenge object from the database
        :param request: The request the user submitted
        :return: (boolean, string)
        """
        return False, "Submission under review"

    @staticmethod
    def solve(user, team, challenge, request):
        """
        This method is not used as llm submission challenges are not solved with flags.

        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        pass

    @staticmethod
    def fail(user, team, challenge, request):
        """
        This method is used to insert Pending into the database in order to mark an answer pending.

        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        data = request.form or request.get_json()
        submission = data["submission"]
        pending = Pending(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(request),
            provided=submission,
        )
        db.session.add(pending)
        db.session.commit()

        grt = GRTSubmission(
            submission_id=pending.id,
            text=data["text"],
            prompt=data["prompt"],
            challenge_id=challenge.id
        )
        db.session.add(grt)
        db.session.commit()

def generate_text(prompt):
    API_URL = "https://api-inference.huggingface.co/models/EleutherAI/gpt-neox-20b"
    headers = {"Authorization": "Bearer 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"}
    payload = { "inputs": prompt }
    response = requests.post(API_URL, headers=headers, json=payload)
    text = response.json()[0]['generated_text'][len(prompt):]
    return text

def load(app):
    # Perform database migrations (if necessary).
    upgrade()
    CHALLENGE_CLASSES["llm_verification"] = LlmSubmissionChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/llm_verification/assets/"
    )
    llm_verifications = Blueprint(
        "llm_verifications", __name__, template_folder="templates"
    )
    # Open the llm_config.toml file and get the host and port
    dir_path = os.path.dirname(os.path.realpath(__file__))
    print(f'Path to llm_verification __init__.py file: {dir_path}')
    config_path = os.path.join(dir_path, "llm_config.toml")
    with open(config_path, "r") as f:
        llm_config = toml.load(f)
        
    llms = {}
    default_llm = llm_config["default_llm"]
    for llm_name, config in llm_config["llms"].items():
        host = config["host"]
        port = config["port"]
        api_key = config["api_key"]
        
        client_llm = ClientLLM(host=host, port=port, api_key=api_key)
        llms[llm_name] = client_llm



    @llm_verifications.route("/generate", methods=["POST"])
    @bypass_csrf_protection
    def generate_for_challenge():
        content = request.json
        challenge_id = content["challenge_id"]
        prompt = content["prompt"]
        challenge = LlmChallenge.query.filter_by(id=challenge_id).first_or_404()
        
        #client_llm = ClientLLM(host='127.0.0.1', port=50055)
        preprompt = challenge.preprompt
        complete_prompt = preprompt + prompt
        try:
            text = generate_text(complete_prompt)
            print(text)
            resp = {
                "success": True,
                "data": {
                    "text": text,
                },
            }
            return jsonify(resp)
        except Exception as e:
            print(e)
            return jsonify({"success": False, "data": {"text": ""}})

        llm = llms.get(challenge.llm, llms[default_llm])


        try:
            generated = llm.sync_generate_text(prompts=[preprompt + prompt])
            print(generated)
            if len(generated.generations) == 0:
                return jsonify({"success": False, "data": {"text": ""}})
            
            text = generated.generations[0][0].text
            resp = {
                "success": True,
                "data": {
                    "text": text,
                },
            }
            return jsonify(resp)
        except Exception as e:
            print(e)
            return jsonify({"success": False, "data": {"text": ""}})

    @llm_verifications.route("/submissions/<challenge_id>", methods=["GET"])
    @authed_only
    def submissions_for_challenge(challenge_id):
        user = get_current_user()
        if get_config("user_mode") == USERS_MODE:
            pending = Pending.query.filter_by(
                challenge_id=challenge_id, user_id=user.id
            ).all()
        else:
            pending = Pending.query.filter_by(
                challenge_id=challenge_id, team_id=user.team_id
            ).all()

        if get_config("user_mode") == USERS_MODE:
            correct = Solves.query.filter(
                Solves.user_id == user.id, Solves.challenge_id == challenge_id
            ).all()
        else:
            correct = Solves.query.filter(
                Solves.team_id == user.team_id, Solves.challenge_id == challenge_id
            ).all()

        if get_config("user_mode") == USERS_MODE:
            incorrect = Fails.query.filter(
                Fails.user_id == user.id, Fails.challenge_id == challenge_id
            ).all()
        else:
            incorrect = Fails.query.filter(
                Fails.team_id == user.team_id, Fails.challenge_id == challenge_id
            ).all()

        if get_config("user_mode") == USERS_MODE:
            awarded = Awarded.query.filter(
                Awarded.user_id == user.id, Awarded.challenge_id == challenge_id
            ).all()
        else:
            awarded = Awarded.query.filter(
                Awarded.team_id == user.team_id, Awarded.challenge_id == challenge_id
            ).all()

        pending = [{"provided": p.provided, "date": isoformat(p.date)} for p in pending]
        correct = [{"provided": c.provided, "date": isoformat(c.date)} for c in correct]
        awarded = [{"provided": a.provided, "date": isoformat(a.date)} for a in awarded]
        incorrect = [
            {"provided": i.provided, "date": isoformat(i.date)} for i in incorrect
        ]

        resp = {
            "success": True,
            "data": {
                "pending": pending,
                "correct": correct,
                "awarded": awarded,
                "incorrect": incorrect,
            },
        }
        return jsonify(resp)

    @llm_verifications.route("/admin/submissions/pending", methods=["GET"])
    @admins_only
    def view_pending_submissions():
        
        filters = {"type": "pending"}

        curr_page = abs(int(request.args.get("page", 1, type=int)))
        results_per_page = 50
        page_start = results_per_page * (curr_page - 1)
        page_end = results_per_page * (curr_page - 1) + results_per_page
        sub_count = Submissions.query.filter_by(**filters).count()
        page_count = int(sub_count / results_per_page) + (
            sub_count % results_per_page > 0
        )

        Model = get_model()

        submissions = (
            Submissions.query.add_columns(
                Submissions.id,
                Submissions.type,
                Submissions.challenge_id,
                Submissions.provided,
                Submissions.account_id,
                Submissions.date,
                Challenges.name.label("challenge_name"),
                Model.name.label("team_name"),
                GRTSubmission.prompt,
                GRTSubmission.text,
            )
            .select_from(Submissions)
            .filter_by(**filters)
            .join(Challenges)
            .join(Model)
            .join(GRTSubmission, GRTSubmission.id == Submissions.id)
            .order_by(Submissions.date.desc())
            .slice(page_start, page_end)
            .all()
        )
        
        return render_template(
            "verify_submissions.html",
            submissions=submissions,
            page_count=page_count,
            curr_page=curr_page,
        )
    
    @llm_verifications.route("/admin/submissions/solved", methods=["GET"])
    @admins_only
    def view_solved_submissions():
        
        filters = {"success": True}

        curr_page = abs(int(request.args.get("page", 1, type=int)))
        results_per_page = 50
        page_start = results_per_page * (curr_page - 1)
        page_end = results_per_page * (curr_page - 1) + results_per_page
        sub_count = GRTSolves.query.filter_by(**filters).count()
        page_count = int(sub_count / results_per_page) + (
            sub_count % results_per_page > 0
        )

        Model = get_model()

        submissions = (
            GRTSolves.query.add_columns(
                GRTSolves.id,
                GRTSolves.challenge_id,
                GRTSolves.prompt,
                GRTSolves.account_id,
                GRTSolves.text,
                GRTSolves.date,
                Challenges.name.label("challenge_name"),
                Challenges.description.label("challenge_description"),
                Model.name.label("team_name"),
            )
            .select_from(GRTSolves)
            .filter_by(**filters)
            .join(Challenges)
            .join(Model)
            .order_by(GRTSolves.date.desc())
            .slice(page_start, page_end)
            .all()
        )
        
        return render_template(
            "solved_submissions.html",
            submissions=submissions,
            page_count=page_count,
            curr_page=curr_page,
        )

    @llm_verifications.route(
        "/admin/verify_submissions/<submission_id>/<status>", methods=["POST"]
    )
    @admins_only
    def verify_submissions(submission_id, status):
        submission = Submissions.query.filter_by(id=submission_id).first_or_404()
        grt_submission = GRTSubmission.query.filter_by(id=submission_id).first_or_404()

        if status == "solve":
            solve = Solves(
                user_id=submission.user_id,
                team_id=submission.team_id,
                challenge_id=submission.challenge_id,
                ip=submission.ip,
                provided=submission.provided,
                date=submission.date,
            )
            db.session.add(solve)
            # Get rid of pending submissions for the challenge
            Submissions.query.filter(
                Submissions.challenge_id == submission.challenge_id,
                Submissions.team_id == submission.team_id,
                Submissions.user_id == submission.user_id,
                Submissions.type == "pending",
            ).delete()
            solve = GRTSolves(
                success=True,
                challenge_id=submission.challenge_id,
                text=grt_submission.text,
                prompt=grt_submission.prompt,
                date=submission.date,
                user_id=submission.user_id,
                team_id=submission.team_id,
            )
            db.session.add(solve)
        elif status == "award":
            awarded = Awarded(
                user_id=submission.user_id,
                team_id=submission.team_id,
                challenge_id=submission.challenge_id,
                ip=submission.ip,
                provided=submission.provided,
            )
            award = Awards(
                user_id=submission.user_id,
                team_id=submission.team_id,
                name="Submission",
                description="Correct Submission for {name}".format(
                    name=submission.challenge.name
                ),
                value=request.args.get("value", 0),
                category=submission.challenge.category,
            )
            db.session.add(awarded)
            db.session.add(award)
            solve = GRTSolves(
                success=True,
                challenge_id=submission.challenge_id,
                text=grt_submission.text,
                prompt=grt_submission.prompt,
                date=submission.date,
                user_id=submission.user_id,
                team_id=submission.team_id,
            )
            db.session.add(solve)
        elif status == "fail":
            wrong = Fails(
                user_id=submission.user_id,
                team_id=submission.team_id,
                challenge_id=submission.challenge_id,
                ip=submission.ip,
                provided=submission.provided,
                date=submission.date,
            )
            db.session.add(wrong)
            solve = GRTSolves(
                success=False,
                challenge_id=submission.challenge_id,
                text=grt_submission.text,
                prompt=grt_submission.prompt,
                date=submission.date,
                user_id=submission.user_id,
                team_id=submission.team_id,
            )
            db.session.add(solve)
        else:
            return jsonify({"success": False})
        db.session.delete(submission)
        db.session.commit()
        db.session.close()
        return jsonify({"success": True})


    app.register_blueprint(llm_verifications)
