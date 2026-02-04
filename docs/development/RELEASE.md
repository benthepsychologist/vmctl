# Release Checklist

This document outlines the process for releasing a new version of VM Workstation Manager.

## Pre-Release Checklist

### Code Quality

- [ ] All tests pass locally: `pytest`
- [ ] Type checking passes: `mypy src/vmws`
- [ ] Linting passes: `ruff check src/vmws tests`
- [ ] Coverage ≥ 80%: `pytest --cov=src/vmws --cov-fail-under=80`
- [ ] CI pipeline passes on GitHub Actions
- [ ] No open critical bugs

### Documentation

- [ ] README.md updated with new features
- [ ] CHANGELOG.md updated with version changes
- [ ] MIGRATION.md updated if behavior changed
- [ ] All public functions have docstrings
- [ ] API changes documented

### Version Update

- [ ] Update version in `src/vmws/__init__.py`
- [ ] Update version in `pyproject.toml`
- [ ] Update CHANGELOG.md with release date
- [ ] Review and update dependencies in pyproject.toml

### Testing

- [ ] Manual smoke testing completed:
  - [ ] `vmws --version` shows correct version
  - [ ] `vmws config` works
  - [ ] `vmws status` works
  - [ ] `vmws start/stop` work
  - [ ] `vmws backup/restore` work
  - [ ] `vmws tunnel` works
- [ ] Test installation from wheel:
  ```bash
  python -m venv test-env
  source test-env/bin/activate
  pip install dist/*.whl
  vmws --version
  ```
- [ ] Test installation from source:
  ```bash
  pip install -e .
  vmws --help
  ```

## Release Process

### 1. Prepare Release

```bash
# Update version (example: 2.1.0)
VERSION="2.1.0"

# Update version in code
sed -i '' "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" src/vmws/__init__.py
sed -i '' "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml

# Commit version bump
git add src/vmws/__init__.py pyproject.toml CHANGELOG.md
git commit -m "Bump version to $VERSION"
```

### 2. Create Git Tag

```bash
# Create annotated tag
git tag -a v$VERSION -m "Release version $VERSION"

# Push tag to GitHub
git push origin v$VERSION
git push origin master
```

### 3. Build Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build wheel and source distribution
python -m build

# Verify contents
twine check dist/*
```

### 4. Test Package Locally

```bash
# Create test environment
python -m venv release-test
source release-test/bin/activate

# Install from wheel
pip install dist/vm_workstation_manager-$VERSION-py3-none-any.whl

# Test basic functionality
vmws --version
vmws --help
vmws config --show

# Cleanup
deactivate
rm -rf release-test
```

### 5. Create GitHub Release

1. Go to: https://github.com/benthepsychologist/vmctl/releases/new
2. Select tag: `v$VERSION`
3. Title: `v$VERSION - [Brief description]`
4. Description: Copy from CHANGELOG.md
5. Attach: `dist/*.whl` and `dist/*.tar.gz`
6. Mark as pre-release if beta/rc
7. Publish release

### 6. Publish to PyPI

```bash
# Test PyPI (optional, for major releases)
twine upload --repository testpypi dist/*

# Verify on Test PyPI
pip install --index-url https://test.pypi.org/simple/ vm-workstation-manager

# Production PyPI
twine upload dist/*
```

### 7. Verify PyPI Release

```bash
# Test installation from PyPI
pip install vm-workstation-manager==$VERSION

# Verify version
vmws --version
```

### 8. Post-Release Tasks

- [ ] Announce release on GitHub Discussions
- [ ] Update any dependent projects
- [ ] Create milestone for next version
- [ ] Close milestone for current version

## Versioning Scheme

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Incompatible API changes
- **MINOR** (x.X.0): New features, backward compatible
- **PATCH** (x.x.X): Bug fixes, backward compatible

Examples:
- `2.0.0` - Major rewrite from bash to Python
- `2.1.0` - Add new command or feature
- `2.1.1` - Bug fix or minor improvement

### Pre-release Versions

- **Alpha**: `2.1.0a1` - Early testing, unstable
- **Beta**: `2.1.0b1` - Feature complete, testing
- **RC**: `2.1.0rc1` - Release candidate, final testing

## Rollback Procedure

If critical issues found after release:

### 1. Yank from PyPI

```bash
# Mark release as broken (doesn't delete)
pip install twine
twine upload --skip-existing --repository pypi dist/*
# Contact PyPI support to yank version
```

### 2. Release Hotfix

```bash
# Create hotfix branch
git checkout -b hotfix/$VERSION
# Fix issue
# Release as PATCH version (e.g., 2.1.2)
```

### 3. Notify Users

- Update GitHub release with warning
- Post in GitHub Discussions
- Update README with known issues

## Continuous Deployment (Future)

When ready for CD:

1. Configure PyPI API token in GitHub Secrets
2. Add publish job to `.github/workflows/release.yml`
3. Auto-publish on tag push

```yaml
# .github/workflows/release.yml
on:
  push:
    tags:
      - 'v*'

jobs:
  pypi-publish:
    name: Publish to PyPI
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install build twine
      - run: python -m build
      - run: twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
```

## Changelog Format

Follow [Keep a Changelog](https://keepachangelog.com/):

```markdown
## [2.1.0] - 2024-11-20

### Added
- New `vmws migrate` command for Cloud Workstation migration
- Support for custom VM machine types

### Changed
- Improved error messages for gcloud failures
- Updated default zone to us-central1-a

### Fixed
- Fixed tunnel port forwarding on macOS
- Fixed config validation for VM names

### Deprecated
- `vmws create` will be replaced by `vmws migrate` in v3.0

### Removed
- Removed bash script installation method

### Security
- Updated dependencies to fix CVE-XXXX-YYYY
```

## Emergency Contacts

- **PyPI Issues**: https://pypi.org/help/
- **GitHub Issues**: https://github.com/benthepsychologist/vmctl/issues
- **Maintainer**: benthepsychologist

## Release Frequency

- **Patch releases**: As needed for critical bugs
- **Minor releases**: Monthly or when features ready
- **Major releases**: Yearly or for breaking changes

## Support Policy

- **Current version**: Full support
- **Previous minor version**: Security fixes only
- **Older versions**: No support, recommend upgrade
