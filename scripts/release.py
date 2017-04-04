#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import subprocess


VER_RE = "__version__ = [\"'](?P<Version>(?:(?![\"']).)*)"
MAJ_UNRELEASED = 'Major release, unreleased\n'
MIN_UNRELEASED = 'Minor release, unreleased\n'


def check_git_is_clean():
    if subprocess.Popen('git diff --quiet', shell=True).wait():
        raise StandardError('uncommitted changes')


def bump_release_version():
    with open(os.path.join(os.getcwd(), 'cuttlepool/__init__.py')) as f:
        init_file = f.read()
        version = re.search(VER_RE, init_file).group('Version')
        if 'dev' not in version:
            raise ValueError('this is not a development version')

        release_version = '.'.join(version.split('.')[:-1])

    init_file = init_file.replace(version, release_version)

    with open(os.path.join(os.getcwd(), 'cuttlepool/__init__.py'), 'w') as f:
        f.write(init_file)

    print 'Bumping version from {} to {}'.format(version, release_version)
    print '-------------------------{}{}\n'.format(
        ''.join(['-' for __ in range(len(version))]),
        ''.join(['-' for __ in range(len(release_version))]))

    return release_version


def tidy_changelog():
    with open(os.path.join(os.getcwd(), 'CHANGELOG.rst')) as f:
        changelog = f.readlines()

    rm_ind = changelog.index(MIN_UNRELEASED)
    if rm_ind == -1:
        rm_ind = changelog.index(MAJ_UNRELEASED)

    if rm_ind == -1:
        print 'Could not find changelog unreleased tag, skipping'
        print '-------------------------------------------------\n'
        return

    del changelog[rm_ind:rm_ind + 2]

    with open(os.path.join(os.getcwd(), 'CHANGELOG.rst'), 'w') as f:
        for line in changelog:
            f.write(line)

    print 'Removed changelog unreleased tag'
    print '--------------------------------\n'


def commit_dev(msg):
    subprocess.Popen('git commit -a -m "{}"'.format(msg),
                     shell=True).wait()
    print 'Committed changes for release'
    print '-----------------------------\n'


def merge_develop():
    subprocess.Popen(
        'git merge develop',
        shell=True).wait()
    print 'Merged into master'
    print '------------------\n'


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


def bump_dev_version():
    with open(os.path.join(os.getcwd(), 'cuttlepool/__init__.py')) as f:
        init_file = f.read()
        version = re.search(VER_RE, init_file).group('Version')
        dev_version = version.split('.')
        dev_version[1] = str(int(dev_version[1]) + 1)
        dev_version.append('dev')
        dev_version = '.'.join(dev_version)

    init_file = init_file.replace(version, dev_version)

    with open(os.path.join(os.getcwd(), 'cuttlepool/__init__.py'), 'w') as f:
        f.write(init_file)

    return dev_version


def unreleased_changelog(release, dev):
    changelog_ver = 'Version {}\n'.format(dev)

    with open(os.path.join(os.getcwd(), 'CHANGELOG.rst')) as f:
        changelog = f.readlines()

    add_ind = changelog.index('Version {}\n'.format(release))

    changelog.insert(add_ind, 'Minor release, unreleased\n\n')
    changelog.insert(add_ind, '{}\n\n'.format('-' * (len(changelog_ver) - 1)))
    changelog.insert(add_ind, changelog_ver)

    with open(os.path.join(os.getcwd(), 'CHANGELOG.rst'), 'w') as f:
        for line in changelog:
            f.write(line)

    print 'Added new section for unreleased version to changelog'
    print '-----------------------------------------------------\n'


def main():
    subprocess.Popen('git checkout develop', shell=True).wait()

    check_git_is_clean()

    version = bump_release_version()

    tidy_changelog()

    msg = 'prepare Cuttle Pool for {} release'.format(version)
    commit_dev(msg)

    subprocess.Popen('git checkout master', shell=True).wait()

    merge_develop()

    git_tag(version)

    upload_pypi(version)

    subprocess.Popen('git checkout develop', shell=True).wait()

    dev_version = bump_dev_version()

    unreleased_changelog(version, '.'.join(dev_version.split('.')[:-1]))

    msg = 'prepare Cuttle Pool for {} development cycle'.format(dev_version)
    commit_dev(msg)


if __name__ == '__main__':
    main()
