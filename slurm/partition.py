import re


required_settings = ['AllowGroups',
                     'AllowAccounts',
                     'MaxTime',
                     'PriorityTier']


class Partition:

    def __init__(self, settings=None, name=None):
        self.name = name
        self.settings = {}
        self.settings_ok = True
        if settings:
            self.parse_settings(settings)

    def parse_settings(self, settings_string):
        tokens = [t for t in re.split('\n | ', settings_string) if t not in ['', '\n']]
        for token in tokens:
            setting, value = token.split('=')
            if setting == 'PartitionName':
                self.name = value
            else:
                self.settings[setting] = value
        for setting in required_settings:
            if setting not in self.settings:
                print(f'Required setting {setting} missing from partition settings')
                self.settings_ok = False

    def check_user(self, user):
        if self.settings['AllowAccounts'] != 'ALL' and user not in self.settings['AllowAccounts']:
            return False
        return True

    def check_groups(self, groups):
        if self.settings['AllowGroups'] == 'ALL':
            return True
        else:
            allowed_groups = self.settings['AllowGroups'].split(',')
            for group in groups:
                if group in allowed_groups:
                    return True
            return False
