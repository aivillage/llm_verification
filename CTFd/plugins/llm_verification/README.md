# Thank You for purchasing an Official CTFd Plugin!

Within this plugin you will find the plugin files for installation.

## Installation

1. Copy the `llm_verification` folder that containes this `README.md` file to the
   `CTFd/plugins` direcotry.

2. Start CTFd and create a challenge. You should see `llm_verification` as an
   option in the `Challenge Type` dropdown.

3. Follow the instructions to create a `llm_verification` challenge.

4. In the admin panel, under the `Plugins` tab, you can access the pending
   submissions page where you will be able to manually approve or reject
   submissions.

## Notes

**Compatible with CTFd v3.0.0**

## Support

If you experience any problems, or if you think you've found a
bug, or have a feature request - please don't hesitate to reach
out to support@ctfd.io.

Thanks again for supporting the CTFd Project!

## Contributing

### tl;dr

Use `docker-compose.dev.yml` for making code changes to CTFd or plugins. Add `--build` for non-code changes such as dependency changes in `requirements.txt` or entrypoint changes in `Dockerfile`.

```console
$ docker compose -f docker-compose.dev.yml up --build
```

To hack on the plugin's code, we want to start [Flask (CTFd's RESTful)](https://flask.palletsprojects.com/en/2.3.x/) in development mode so code changes trigger hot reloads.

Since the repo directory's already mounted as a [volume](https://docs.docker.com/storage/volumes/) in `docker-compose.yml`, container images don't need to be rebuilt for code changes to take effect. However, (the production server) Gunicorn won't recognize these changes, so we need to start it with Flask instead.

The `Dockerfile.dev`, `docker-compose.dev.yml`, and `docker-entrypoint.dev.sh` are near-exact copies of `Dockerfile`, `docker-compose.yml`, and `docker-entrypoint.sh`. `Dockerfile.dev` uses a different entrypoint (`docker-entrypoint.dev.sh`) and `docker-compose.dev.yml` uses a [different Dockerfile for builds](https://docs.docker.com/compose/compose-file/build/#illustrative-example). They work together to start the application with Flask instead of Gunicorn (via `docker-entrypoint.dev.sh`).

To use it, specify it with `-f` when invoking `docker compose up`. 

```console
$ docker compose -f docker-compose.dev.yml up
```

For dependency and Dockerfile changes to take effect, add `--build`. This will take longer, though, because some layers will need to be rebuilt.

```console
$ docker compose -f docker-compose.dev.yml up --build
```

To start over from a clean slate, ensure that no CTFd containers are running with `docker ps` and `docker kill`. Then run `rm -rf ./.data`.
