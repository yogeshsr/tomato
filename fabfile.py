# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

from fabric.api import run, sudo, env
from fabric.context_managers import cd, settings
import os
import sys

PROJECT_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(PROJECT_DIR, '../../src'))


def git_clone_if_not_present(code_dir):
    if run("test -d %s" % code_dir).failed:
        run("git clone git://github.com/mangroveorg/mangrove.git %s" % code_dir)


def activate_and_run(virtual_env, command):
    run('source %s/bin/activate && ' % virtual_env + command)


def branch_exists(branch_name):
    return not run("git branch -a|grep %s" % branch_name).failed


def sync_develop_branch():
    run("git checkout develop")
    run("git pull origin develop")


def delete_if_branch_exists(build_number):
    if branch_exists(build_number):
        run("git branch -D %s" % build_number)


def restart_gunicorn(virtual_env):
    if gunicorn_is_running():
        stop_gunicorn()
    start_gunicorn(virtual_env)


def gunicorn_is_running():
    return not run("pgrep gunicorn").failed


def stop_gunicorn():
    run("kill -9 `pgrep gunicorn`")


def start_gunicorn(virtual_env):
    activate_and_run(virtual_env, "gunicorn_django -D -b 0.0.0.0:8000 --pid=mangrove_gunicorn")


def deploy(build_number, home_dir, virtual_env, environment="test"):
    """build_number : hudson build number to be deployed
       home_dir: directory where you want to deploy the source code
       virtual_env : path to your virtual_env folder
    """
    ENVIRONMENT_CONFIGURATIONS = {
                                    "showcase": {"SITE_ID": 2},
                                    "test": {"SITE_ID": 4}
                                 }

    if(build_number == 'lastSuccessfulBuild'):
        build_number = run("curl http://178.79.163.33:8080/job/Mangrove-develop/lastSuccessfulBuild/buildNumber")

    run("export COMMIT_SHA=`curl http://178.79.163.33:8080/job/Mangrove-develop/%s/artifact/last_successful_commit_sha`" % (build_number,))

    code_dir = home_dir + '/mangrove'
    with settings(warn_only=True):
        git_clone_if_not_present(code_dir)
        with cd(code_dir):
            run("git reset --hard HEAD")
            sync_develop_branch()
            delete_if_branch_exists(build_number)
            run("git checkout -b %s $COMMIT_SHA" % (build_number, ))
            run("git checkout .")
            activate_and_run(virtual_env, "pip install -r requirements.pip")
        with cd(code_dir + '/src/datawinners'):
            activate_and_run(virtual_env, "python manage.py syncdb")
            restart_gunicorn(virtual_env)


def showcase(home_dir):
    env.user = "mangrover"
    env.hosts = ["178.79.161.90"]
    env.key_filename = ["/home/mangrover/.ssh/id_dsa"]
    app_dir = home_dir + '/mangrove/src/datawinners'
    with cd(app_dir)
        run("cp showcase_local_settings.py local_settings.py")


def test(home_dir):
    app_dir = home_dir + '/mangrove/src/datawinners'
    with cd(app_dir)
        run("cp test_local_settings.py local_settings.py")
