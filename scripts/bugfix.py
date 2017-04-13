#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import subprocess


VER_RE = "__version__ = [\"'](?P<Version>(?:(?![\"']).)*)"


def check_git_is_clean():
    if subprocess.Popen('git diff --quiet', shell=True).wait():
        raise StandardError('uncommitted changes')


def bump_bugfix_version():
    with open(os.path.join(os.getcwd(), 'cuttlepool/__init__.py')) as f:
        init_file = f.read()
        version = re.search(VER_RE, init_file).group('Version')
        if 'dev' in version:
            raise ValueError('this is not a released version')

    release_version = version.split('.')
    release_version[2] = str(int(release_version[2]) + 1)
    release_version = '.'.join(release_version)

    init_file = init_file.replace(version, release_version)

    with open(os.path.join(os.getcwd(), 'cuttlepool/__init__.py'), 'w') as f:
        f.write(init_file)

    print 'Bumping version from {} to {}'.format(version, release_version)
    print '-------------------------{}{}\n'.format(
        ''.join(['-' for __ in range(len(version))]),
        ''.join(['-' for __ in range(len(release_version))]))

    return release_version


def commit(msg):
    subprocess.Popen('git commit -a -m "{}"'.format(msg),
                     shell=True).wait()
    print 'Committed changes for release'
    print '-----------------------------\n'


def git_tag(version):
    subprocess.Popen(
        'git tag v{}'.format(version),
        shell=True).wait()
    print 'v{} tag added to master'.format(version)
    print '---------------------{}\n'.format(''.join(['-' for __ in range(len(version))]))


def upload_pypi(version):
    subprocess.Popen(('. venv/bin/activate && '
                      'python setup.py sdist bdist_wheel && '
                      'twine upload dist/cuttlepool-{}*').format(version),
                     shell=True).wait()
    print 'Uploaded to PyPI'
    print '----------------\n'


def main():
    subprocess.Popen('git checkout master', shell=True).wait()

    check_git_is_clean()

    version = bump_bugfix_version()

    msg = 'prepare Cuttle Pool for {} release'.format(version)
    commit(msg)

    git_tag(version)

    upload_pypi(version)


if __name__ == '__main__':
    main()
