# Versioning

The project uses release versioning a format `YY.MM.DD` (both for pip packages and image tags). For instance, when releasing a version on Sep 15, 2021, it would be versionsed as `21.9.15` (no zero before `9`).


# Release process

Suppose, today is October 15, 2020, and we want to update both apolo-extras pip package and docker image.

0. Run `make setup` with Poetry installed and make sure all tests are green in `master`.

1. Bump code version in release branch.
    - update `apolo_extras/version.py`: set `__version__ = "20.10.15"`;
    - `git switch -c release/20.10.15`;
    - run `make changelog-draft` and verify changelog looks valid;
    - run `make changelog` - this will delete changelog items from `CHANGELOG.D`;
    - `git add CHANGELOG* apolo_extras/version.py && git commit -m "Release v$(python apolo_extras/version.py)"` and `git push -u origin $(git branch --show-current)`;
    - wait for green build in [Actions](https://github.com/neuro-inc/apolo-extras/actions), get approve and merge to `master`;

2. CD validates the release notes and releases the merged version automatically.
    - publishes the package to PyPI and the versioned image to GHCR;
    - creates the `v20.10.15` tag at the merged commit and a GitHub release with automatically generated release notes;
    - checks that `CHANGELOG.md` contains the version tag; CI does not edit the changelog;
    - final releases also update the `latest` image tag;
    - pushes without a version change and versions that are already tagged do not release;
    - if publishing fails, rerun the failed jobs in [Actions](https://github.com/neuro-inc/apolo-extras/actions); already uploaded PyPI files are skipped;
    - verify that `pip install -U apolo-extras` installs `apolo-extras==20.10.15`.

The existing PyPI trusted publisher must allow `.github/workflows/cd.yaml` with
the `pypi` environment, and that environment must allow deployments from `master`.
GitHub Actions also needs permission to write repository contents and packages.
No manual tag push or GitHub release is required.


# Alpha release

To debug a release process without changing latest versions of package and image, you can issue an alpha release just postfixing the version with `a`:
- `20.10.15a1`
- `20.10.15a2`

Merge the version and generated changelog through the same process. CI marks the
GitHub release as a prerelease and does not update the `latest` image tag.
