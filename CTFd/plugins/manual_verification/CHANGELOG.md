# 1.1.1 / 2021-03-26

- Fix plugin when working under CTFd v3.3.0
- Simplify plugin to take more advantage of the existing challenge base class

# 1.1.0 / 2020-07-21

- Update plugin to work with CTFd v3
  - HTML template files are now written in Jinja for rendering by the CTFd server instead of the browser

# 1.0.4 / 2020-05-21

- Fix issue textarea input and black backgrounds
- Fix issue where users cancel out when inputting award points
- Fix issue where pressing Enter on the submission input would incorrectly submit

# 1.0.3 / 2020-05-08

- Add plugin migrations for database to support CTFd v2.4.0

# 1.0.2 / 2020-02-26

- Fix issue where hints could not be loaded

# 1.0.1 / 2020-01-07

- Fix submitted answers rendering in the challenge UI
- Added `Moment()` and `htmlEntities()` fallbacks because they aren't currently exposed to CTFd plugins

# 1.0.0 / 2020-01-04

- Update theme to support CTFd v2.2.0
- Begin tracking changes in `CHANGELOG.md`
