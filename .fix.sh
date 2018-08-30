#!/bin/bash -e

# Clean your git project. It's recommended to run it as a pre-push hook.
#
# You can force to run this script on every push/commit (but it significantly increases time).
# To do that just run it once in the root of your project:
# $ bash .fix.sh --pre-push
# $ bash .fix.sh --pre-commit
#
# It will then run automatically every time you want to push/commit something.
#
# To disable this hook while push/commit use:
# $ git push/commit --no-verify
# Or simply delete it:
# $ rm .git/hooks/pre-push
#
# Requirements:
# bash, sed, xargs, md5sum, awk, git, python


DIR_PATH=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=${DIR_PATH}
[[ "$ROOT" == */.git/hooks ]] && ROOT=${ROOT}/../../
# ROOT=$(realpath --relative-to="$PWD" "$ROOT")
# the previous version with --relative-to depends on not-widely-available
# GNU coreutils 8.23
# so the python-flavored instead https://stackoverflow.com/a/7305217
ROOT=$(python -c "import os; print(os.path.relpath('$ROOT', '$PWD'))")


function update_hook() {
    hook_name=${1-pre-push}
    # put this file into your .git/hooks/ folder
    [[ "$DIR_PATH" == */.git/hooks ]] || {
        HOOK_DIR="$DIR_PATH/.git/hooks"
        HOOK_PATH="$HOOK_DIR/$hook_name"
        [ -d "$HOOK_DIR" ] || {
            echo "$HOOK_DIR directory does not exist. Ensure that the hook is in the root of the git-tracked project." >&2
            exit 1
        }

        rm -f "$HOOK_PATH"
        ln -rs $0 "$HOOK_PATH" && echo "Link .git/hooks/$hook_name updated"
    }
}


function common_amends() {
    file="$1"
    if ! [[ -f "$file" ]]; then
        return
    fi
    # do not amend symlinks
    if [[ -h "$file" ]]; then
        return
    fi

    #echo "amend $file"

    # dos2unix
    sed -i 's/\r$//' "$file"

    # remove trailing spaces
    sed -i 's/[[:blank:]]*$//' "$file"

    # expand tabs
    sed -i 's/\t/    /g' "$file"

    # ensure the blank line
    echo >> "$file"
    # remove leading and trailing blank lines
    # http://stackoverflow.com/a/7359879/
    sed -i -e :a -e '/./,$!d;/^\n*$/{$d;N;};/\n$/ba' "$file"
}


function check_syntax() {
    file="$1"
    #echo "check syntax in $file"

    #[[ "$file" == *.py ]] && python -mpy_compile "$file"
    [[ "$file" == *.sh ]] && bash -n "$file"
    return 0
}


function git_ls_no_submodules() {
    if [[ -f .gitmodules ]]; then
        # manually exclude submodules https://stackoverflow.com/a/48434067
        git ls-files $@ | grep -Fxvf  <(grep "^\s*\[submodule " .gitmodules | cut -d '"' -f2)
    else
        git ls-files $@
    fi
}


ALLOW_NON_ASCII_FILE_TYPES='rst|md'

function check_unicode() {
    # all git-tracked *.py files (if exists any)
    # should have `from __future__ import unicode_literals`
    # except for empty files (the ones whose 'wc -l'==0)
    not_declared_unicode=$(
        for f in $(git ls-files '*.py'); do
            if [[ ! -s ${f} ]] || grep -Lq unicode_literals ${f}; then
                continue
            fi
            echo ${f}
        done
    )

    if [[ "$not_declared_unicode" ]]; then
        echo 'Not declared `from __future__ import unicode_literals`:'
        for i in ${not_declared_unicode}; do
            echo ${i};
        done
        false
    fi

    # all git-tracked *.py files (if exists any) should not have
    # a 'u' prefix before string literal
    ! git ls-files '*.py' | xargs grep -nPI "[^a-zA-Z\x7F-\xFF]u['\\\"]"

    ! git_ls_no_submodules "*[^.($ALLOW_NON_ASCII_FILE_TYPES)]" | xargs grep -nPIr --color '[^\x00-\x7F]'
}

# =================== HERE IS THE 'MAIN' FUNCTION BEGINS =================== #

case "$1" in
    '')
        ;;
    --pre-commit)
        update_hook "${1:2}"
        ;;

    --pre-push)
        update_hook "${1:2}"
        ;;

    --unicode)
        # disable the glob
        set -o noglob
        check_unicode
        set +o noglob
        ;;

    *)
        echo "Invalid arg: $1" >&2
        exit 1
esac

# Add your favorite extensions here
# get all the extensions you have with
# $ git ls-files | sed 's|.*\.||' | sort -u
KNOWN_EXTENSIONS='py|ipynb|php|sql|sh|js|html|htm|css|json|xml|yml|yaml|iml|csv|md|rst|txt|conf|cfg|ini|in|gitignore'

# check if any git-tracked files has been changed
hash_file=$(tempfile) || exit 1
trap "rm -f -- '$hash_file'" EXIT
git_ls_no_submodules | xargs md5sum > "$hash_file"

# http://stackoverflow.com/a/8694751/
IFS=$'\n'
for file in $(git ls-files | grep -iP ".*\.($KNOWN_EXTENSIONS)$"); do
    common_amends "$file"
    check_syntax "$file"
done

for file in $(git submodule foreach 'git ls-files | sed "s|^|$path/|"' | grep -iP ".*\.($KNOWN_EXTENSIONS)$"); do
    common_amends "$file"
    check_syntax "$file"
done
unset IFS


fixed_files=$(diff <(git_ls_no_submodules | xargs md5sum) "$hash_file" | grep -P '^[<>]' | awk '{print $3}' | sort -u)
rm -f -- "$hash_file"
trap - EXIT

if [[ "$fixed_files" ]]; then
    echo "Fixed files:" >&2
    echo "$fixed_files" >&2
    echo -e "\nConsider adding them to commit (git add -p ...)" >&2
    exit 2
fi
