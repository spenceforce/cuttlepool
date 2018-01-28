#!/usr/bin/env bash
# CuttlePool release script
# Usage:
# ./release VERSION_INCREMENT
# where VERSION_INCREMENT is either major, minor, or patch.

. venv/bin/activate

RESUME='release.resume'
UNRELEASED='Unreleased'
DATE=$(date +%Y-%m-%d)
INCREMENT=$(echo "$1" | tr '[:upper:]' '[:lower:]')

function clean_build {
    rm -rf build/ dist/ *.egg-info
}

function resume_release {
    # Resume release process.
    read -a info < $RESUME
    ${info[0]} ${info[@]:1}
    exit 0
}

function new_version {
    v=(${2//./ })
    case $1 in
	"major") echo "$(expr ${v[0]} + 1).0.0-dev" ;;
        "minor") echo "${v[0]}.$(expr ${v[1]} + 1).0-dev" ;;
	"patch") echo "${v[0]}.${v[1]}.$(expr ${v[2]} + 1)-dev" ;;
	*) echo "release: Could not create new dev version." >&2; exit 1;;
    esac
}

function build {
    echo -e "build\t$1\t$2" > $RESUME
    python setup.py sdist bdist_wheel
    if [ $? -ne 0 ]
    then
	clean_build
	echo "release: Problem building package." >&2
	exit 1
    fi
    test_pypi $1 $2
}

function test_pypi {
    echo -e "test_pypi\t$1\t$2" > $RESUME
    twine upload --repository-url https://test.pypi.org/legacy/ dist/*
    if [ $? -ne 0 ]
    then
	echo "release: Problem uploading to TestPyPI." >&2
	exit 1
    fi

    # Let user ensure package can be installed from Test PYPi.
    read -p "Can package be installed from TestPYPi properly? [y/N] " resp
    case $answer in
	[yY]) ;;
	*) echo "release: Pausing release. Release script will resume from this point." >&2; exit 1;;
    esac
    pypi $1 $2
}

function pypi {
    echo -e "pypi\t$1\t$2" > $RESUME
    twine upload dist/*
    if [ $? -ne 0 ]
    then
	echo "release: Problem uploading to PyPI." >&2
	exit 1
    fi
    git_push $1 $2
}

function git_push {
    echo -e "git_push\t$1\t$2" > $RESUME
    branch=$(git rev-parse --abbrev-ref HEAD)
    git push origin "$branch"
    if [ $? -ne 0 ]
    then
	echo "release: Problem pushing to GitHub." >&2
	exit 1
    fi
    git_push_tag $1 $2
}

function git_push_tag {
    echo -e "git_push_tag\t$1\t$2" > $RESUME
    git push origin "v$2"
    if [ $? -ne 0 ]
    then
	echo "release: Problem pushing tag to GitHub." >&2
	exit 1
    fi
    prepare_development $1 $2
}

function prepare_development {
    echo -e "prepare_development\t$1\t$2" > $RESUME
    DEV_VERSION=$(new_version $1 $2)
    # Update changelog.
    sed -i "/\[$2\]/i## [$UNRELEASED]\n" CHANGELOG.md
    if [ $? -ne 0 ]
    then
	git checkout HEAD -- CHANGELOG.md
	echo "release: Problem updating CHANGELOG.md for development." >&2
	exit 1
    fi

    # Update version.
    sed -i "s/$2/$DEV_VERSION/" cuttlepool.py
    if [ $? -ne 0 ]
    then
	git checkout HEAD -- CHANGELOG.md cuttlepool.py
	echo "release: Problem updating __version__ in cuttlepool.py for development." >&2
	exit 1
    fi

    # Commit for release.
    git add CHANGELOG.md cuttlepool.py
    if [ $? -ne 0 ]
    then
	git checkout HEAD -- CHANGELOG.md cuttlepool.py
	echo "release: There was a problem adding the files for development." >&2
	exit 1
    fi
    git commit -m 'Bump version for development'
    if [ $? -ne 0 ]
    then
	git checkout HEAD -- CHANGELOG.md cuttlepool.py
	echo "release: There was a problem committing the files for development." >&2
	exit 1
    fi

    git_push_development
}

function git_push_development {
    echo -e "git_push_development" > $RESUME
    branch=$(git rev-parse --abbrev-ref HEAD)
    git push origin "$branch"
    if [ $? -ne 0 ]
    then
	echo "release: Problem pushing development to GitHub." >&2
	exit 1
    fi

    rm -f $RESUME
    clean_build
    exit 0
}

# Resume release if it was paused.
if [ -f $RESUME ]
then
    resume_release
fi

# Check VERSION_INCREMENT is valid.
case $INCREMENT in
    major) ;;
    minor) ;;
    patch) ;;
    *)
	echo "release: Invalid version increment. Valid: major, minor, or patch." >&2
	exit 1
esac

# Check git is clean.
git diff --quiet
if [ $? -ne 0 ]
then
    echo "release: This git branch has uncommitted changes." >&2
    exit 1
fi

# Strip the "dev" tag from the version.
DEV_VERSION=$(python setup.py -V 2>/dev/null)
if [[ $DEV_VERSION != *"dev"* ]]
then
    echo "release: Version $DEV_VERSION is not a candidate for release." >&2
    exit 1
fi
VERSION=${DEV_VERSION%.*}

# Begin release process.

# Update changelog.
count=$(gawk -v old="\\\\[$UNRELEASED\\\\]" -v new="[$VERSION] - $DATE" '{ count+=gsub(old, new) } END{ print count }' CHANGELOG.md)
if [ $count -ne 1 ]
then
    echo "release: Improper number of replacements in CHANGELOG.md $count" >&2
    exit 1
fi

gawk -i inplace -v old="\\\\[$UNRELEASED\\\\]" -v new="[$VERSION] - $DATE" '{ gsub(old, new) }; { print }' CHANGELOG.md
if [ $? -ne 0 ]
then
    git checkout HEAD -- CHANGELOG.md
    echo "release: Problem updating CHANGELOG.md." >&2
    exit 1
fi

# Update version.
count=$(gawk -v old="__version__ = [\"']${VERSION}-dev[\"']" -v new="__version__ = '${VERSION}'" '{ count+=gsub(old, new) } END{ print count }' cuttlepool.py)
if [ $count -ne 1 ]
then
    echo "release: Improper number of replacements in cuttlepool.py $count" >&2
    exit 1
fi
gawk -i inplace -v old="__version__ = [\"']${VERSION}-dev[\"']" -v new="__version__ = '${VERSION}'" '{ gsub(old, new) }; { print }' cuttlepool.py
if [ $? -ne 0 ]
then
    git checkout HEAD -- CHANGELOG.md cuttlepool.py
    echo "release: Problem updating __version__ in cuttlepool.py." >&2
    exit 1
fi

# Commit for release.
git add CHANGELOG.md cuttlepool.py
if [ $? -ne 0 ]
then
    git checkout HEAD -- CHANGELOG.md cuttlepool.py
    echo "release: There was a problem adding the files." >&2
    exit 1
fi
git commit -m "Release $VERSION"
if [ $? -ne 0 ]
then
    git checkout HEAD -- CHANGELOG.md cuttlepool.py
    echo "release: There was a problem committing the files." >&2
    exit 1
fi

# Create git tag
git tag -a "v$VERSION" -m "Release $VERSION"
if [ $? -ne 0 ]
then
    git checkout HEAD~1 -- CHANGELOG.md cuttlepool.py
    # Since the release is aborting, in the off chance the tag was created,
    # the tag needs to be removed since the commit it points to no longer
    # exists.
    git tag -d $(git tag)
    git fetch --tags
    echo "release: There was a problem creating the git tag." >&2
    exit 1
fi
    

# Most actions from this point involve remote servers. The last successful
# action will be saved in `release.resume` with any necessary info to resume
# operations from that point. From this point forward, the release will be
# resumed from the resume filejust by calling `./release.sh`. If there
# is a failure, correct the failure and resume the release.
# NOTE: Calling `./release.sh VERSION_INCREMENT` will also resume the release
# and will ignore VERSION_INCREMENT.
build $INCREMENT $VERSION	# All further function calls are chained.
exit 0
