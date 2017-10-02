#!/usr/bin/env python

import os
import sys
import requests
import argparse
import json
import MySQLdb
import time

class createUser(object):
    def __init__(self, config):
        """Initilize createUser and set additonal configuration data."""
        self.config = config
        self.db = MySQLdb.connect(host=self.config['mysql']['host'],
                     user=self.config['mysql']['user'],
                     passwd=self.config['mysql']['password'],
                     db=self.config['mysql']['database'])

        self.cur = self.db.cursor()
        self.cur.execute("SELECT secret FROM clients WHERE slug='ghost-admin'")
        self.config['secret'] = self.cur.fetchone()[0]
        sql = "SELECT `id` FROM `roles` WHERE `name`=%s"
        self.cur.execute(sql, (config['role_name'],))
        self.config['role_id'] = self.cur.fetchone()[0]


    def authenticate(self):
        """Authenticate to get Bearer token and set headers."""
        self.session = requests.Session()

        url = "%s/ghost/api/v0.1/authentication/token" % ( self.config['base_url'] )
        data = {
            'grant_type': 'password',
            'username': self.config['admin'],
            'password': self.config['admin_password'],
            'client_id': 'ghost-admin',
            'client_secret': self.config['secret']
            }

        r = self.session.post(url, data=data, verify=False)
        if r.status_code == 200:
            self.config['headers'] = {
                'authorization': 'Bearer %s' % (r.json()['access_token']),
                'accept':'application/json, text/javascript, */*',
                'content-type':'application/x-www-form-urlencoded'
                }
            print('Successfully authenticated as user: %s\n' % (self.config['admin']) )
        else:
            print('Error: Unable to authenticate with user: %s\n' % (self.config['admin']) )


    def getInvite(self):
        """Creates the user invite."""

        url = "%s/ghost/api/v0.1/invites/" % ( self.config['base_url'] )
        data = {
            "invites[0][email]": self.config['email'],
            "invites[0][role_id]": self.config['role_id']
            }
        r = self.session.post(url, data=data, verify=False, headers=self.config['headers'])
        if r.status_code == 200:
            print('Invite for %s created successfully.' % (self.config['email']) )
        else:
            print('Invite for %s failed. Error: %s' % (self.config['email'], r.text) )


    def mysqlGetInvite(self):
        self.db.commit()
        sql = "SELECT `token` FROM `invites` WHERE `email`=%s"
        self.cur.execute(sql, (self.config['email'],))
        token = self.cur.fetchone()[0]
        self.config['invite_token'] = token
        self.config['invite_url'] = token.rstrip('=')


    def signupUser(self):

        url = "%s/ghost/api/v0.1/authentication/invitation/" % ( self.config['base_url'] )
        data = {
                "invitation[0][name]": self.config['name'],
                "invitation[0][email]": self.config['email'],
                "invitation[0][password]": self.config['password'],
                "invitation[0][token]": self.config['invite_token']
            }

        r = self.session.post(url, data=data, verify=False)
        print(r.request.headers)

        if r.status_code == 200:
            return True
        else:
            return False

    def run(self):
        self.authenticate()
        self.getInvite()
        time.sleep(5)
        self.mysqlGetInvite()

        if self.signupUser():
            print('User: %s was successfully setup.' % (self.config['name']) )
        else:
            print('User: %s failed to be setup.' % (self.config['name']) )

        self.db.close()




if __name__ == '__main__':
    role_choices = ['Administrator', 'Editor', 'Author', 'Owner' ]
    parser = argparse.ArgumentParser(description="GHOST Add User",epilog=None)
    parser.add_argument("-c","--config",help="Ghost configuration file",type=str,default='/',required=False)
    parser.add_argument('--admin',help="Ghost Administrator Account",type=str,required=True)
    parser.add_argument('--admin_password',help="Ghost Administrator Password",type=str,required=True)
    parser.add_argument('-n',"--name",help="Full Name of new user",type=str,required=True)
    parser.add_argument('-e',"--email",help="Email address of new user",type=str,required=True)
    parser.add_argument('-p',"--password",help="Password for new user",type=str,required=True)
    parser.add_argument('--role',help="Role type for user",choices=role_choices,required=True)
    opt = parser.parse_args()

    config = {}

    if opt.config:
        if os.path.isfile(opt.config):
            config['config_file'] = opt.config
        else:
            config['config_file'] = '/var/www/ghost/config.production.json'
    else:
        config['config_file'] = '/var/www/ghost/config.production.json'

    with open(config['config_file'], 'r') as f:
        json_data = json.load(f)

    if json_data['database']['client'] == 'mysql':
        config['mysql'] = {}
        config['mysql']['database'] = json_data['database']['connection']['database']
        config['mysql']['user'] = json_data['database']['connection']['user']
        config['mysql']['password'] = json_data['database']['connection']['password']
        config['mysql']['host'] = json_data['database']['connection']['host']
    #else:
        #add support for sqlite

    config['admin'] = opt.admin
    config['admin_password'] = opt.admin_password
    config['base_url'] = 'https://127.0.0.1' #json_data['url']
    config['name'] = opt.name
    config['email'] = opt.email
    config['password'] = opt.password
    config['role_name'] = opt.role

    createUser(config).run()
