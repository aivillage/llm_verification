# 🤖 LLM Verification Plugin

The LLMM Verification Plugin ("LLMV") is a [CTFd](https://github.com/CTFd/CTFd) plugin that adds a new challenge type called "LLM Verification." This new challenge type tasks users with creating prompts for external LLM APIs (such as [gpt-neox-20b](https://huggingface.co/EleutherAI/gpt-neox-20b)) that generate cheeky responses. These responses are reviewed manually by graders, who assign points based on how successfully the answer managed to subvert the model.

## 🖥️ Installation

1. Copy the `llm_verification` folder that contains this `README.md` file to `CTFd/plugins/`.

2. Copy the template config file (`llmv_config.template.json`) from `CTFd/plugins/llm_verification/ and remove `.template` from the filename.

   ```console
   $ cp CTFd/plugins/llm_verification/llmv_config.template.json CTFd/plugins/llm_verification/llmv_config.json
   ```

3. Replace `"UNSET"` values `llmv_config.json` with the values that you desire.

4. Confirm that LLMV installed successfully. Look for this message after running `docker compose up`.

   ```
   INFO - Initialized LLM Verification Plugin
   ```

## ⛳️ Usage

1. Create a CTFd event.

2. Login to CTFd as an administrator.

3. Click `Admin Panel" on the right side of the top toolbar.

4. Click "Challenges" in middle of the top toolbar.

5. Click the `⨁` in the "Challenges" page's title (`Challenges ⨁`).

6. Create a challenge with "llm_verification" selected as the "Challenge Type."

   a. Name (optional): challenge title.

   b. Category (optional): general "type" of challenge that's used to visually group challenges.

      1. ex. "pre-prompt extraction"
      2. ex. "insensitive output"

   c. Message (optional): Describe the goal for your users.

   d. Pre-prompt (optional): A string that will be prepended to every prompt that users submit to this challenge. Be sure to leave a space at the end.

   e. LLM to use (optional, defaults to "VanillaNeox"): The LLM to use for this challenge.

   f. Value (required): This isn't used, but you need to add an integer to proceed.

   g. Click the "Create" button in the lower right, which will present you with an "Options" popup.

   h. Flag (optional): This value isn't used and can be ignored.

   i. State (optional): Set to "Visible" so users can see your new challenge.

7. Click "CTFd" on the left of the top toolbar. This exits the "Admin Panel."

8. Click "Challenges" in the middle of the top toolbar. This shows challenges as users see them.

9. Select the challenge that you created.

10. Add some text to the "Prompt" text box.

11. Click the "Generate" button. Generated text will appear in the second box. If you'd like to change the text that was generated, then change the prompt and click "Generate" again. Previously generated text in the second box will be replaced.

12. Click the "Submit" button. A red notification will pop up saying "Submission Under Review."

13. Click "Admin Panel" in the right of the top panel.

14. Click the "Plugins" dropdown in the right of the top panel.

15. Click "LLM Submissions" to navigate to the grading page for answer submissions.

16. Click the 💬 ("Grade") button on the far right of an answer submission's row.

17. Click "Mark Incorrect," "Mark Correct," or "Award Points."
   a. 🟥 "Mark Incorrect:" Delete the user's submission and don't award them points.
   b. 🟩 "Mark Correct:" Award the amount of points set earlier in "Options" and prevent the user from submitting additional answers. The challenge's card will be turn green and gain a ✅. The user will still be able to generate responses for the challenge, but clicking the "Submit" button will create a blue dialog that says "You already solved this."
   c. ◻️"Award Points:" Award a custom amount of points and allow the user to submit additional answers.
   d. Note that points awarded with "Award Points" won't immediately show up in "Admin Panel"'s "Scoreboard", but they will show up immediately in the non-admin panel's "Scoreboard"

## 🛠️ Contributing

### 📖 tl;dr

Use `docker-compose.dev.yml` for making code changes to CTFd or plugins. Add `--build` for non-code changes such as dependency changes in `requirements.txt` or entrypoint changes in `Dockerfile`. CTFd will be available at [https://localhost:8000](https://localhost:8000).

   ```console
   $ docker compose -f docker-compose.dev.yml up --build
   ```

### 👩🏼‍💻 Development Mode

To hack on the plugin's code, we want to start [Flask (CTFd's RESTful)](https://flask.palletsprojects.com/en/2.3.x/) in development mode so code changes trigger hot reloads.

Since the repo directory's already mounted as a [volume](https://docs.docker.com/storage/volumes/) in `docker-compose.yml`, container images don't need to be rebuilt for code changes to take effect. However, (the production server) Gunicorn won't recognize these changes, so we need to start it with Flask instead.

The `Dockerfile.dev`, `docker-compose.dev.yml`, and `docker-entrypoint.dev.sh` are near-exact copies of `Dockerfile`, `docker-compose.yml`, and `docker-entrypoint.sh`. `Dockerfile.dev` uses a different entrypoint (`docker-entrypoint.dev.sh`) and `docker-compose.dev.yml` uses a [different Dockerfile for builds](https://docs.docker.com/compose/compose-file/build/#illustrative-example). They work together to start the application with Flask instead of Gunicorn (via `docker-entrypoint.dev.sh`).

To use it, specify it with `-f` when invoking `docker compose up`.

   ```console
   $ docker compose -f docker-compose.dev.yml up
   ```

### 🏗️ Rebuilding

For dependency and Dockerfile changes to take effect, add `--build`. This will take longer, though, because some layers will need to be rebuilt.

   ```console
   $ docker compose -f docker-compose.dev.yml up --build
   ```

To start over from a clean slate, ensure that no CTFd containers are running with `docker ps` and `docker kill`. Then run `rm -rf ./.data`.

## 🐭 Miscellaneous

### 🔌 Compatibility

(Presumably) **Compatible with CTFd `v3.0.0`**

Built with CTFd `v3.5.1`

### 🛟 Support

If you experience any problems, or if you think you've found a
bug, or have a feature request - please don't hesitate to reach
out to support@ctfd.io.

### 🙏🏻 Kudos

Readme format inspired by [makeareadme.com](https://www.makeareadme.com).

## 🪪 License

Must be 16 or older and have an adult in the car during operation.
