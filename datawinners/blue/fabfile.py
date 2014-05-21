from fabric.context_managers import cd
from fabric.contrib.console import confirm
from fabric.operations import sudo
from fabric.state import env


'''
To update the dcsweb.twhosted with new code and restart server, run
fab qa deploy
from $HOME/workspace/datawinners/datawinners/blue

'''


MANGROVER = 'mangrover'
DCS = '/home/mangrover/workspace/datawinners'
MANGROVE_CODE = '/home/mangrover/virtual_env/datawinners/src/mangrove'

def deploy():
    if confirm('Continue to update the application code?'):
        deploy_mangrove()
        deploy_dcs()
        restart_uwsgi()

def qa():
    env.hosts = ['172.18.29.2']

def deploy_mangrove():
    with cd(MANGROVE_CODE):
        sudo('git pull --rebase team develop-dcs', user=MANGROVER)

def deploy_dcs():
    with cd(DCS):
        sudo('git pull --rebase team develop-dcs-dw', user=MANGROVER)

def restart_uwsgi():
    sudo("service uwsgi restart")

