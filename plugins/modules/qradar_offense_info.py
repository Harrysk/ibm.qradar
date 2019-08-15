#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2019, Adam Miller (admiller@redhat.com)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}
DOCUMENTATION = '''
---
module: qradar_offense_info
short_description: Obtain information about one or many QRadar Offenses, with filter options
description:
  - This module allows to assign, protect, follow up, set status, and assign closing reason to QRadar Offenses
version_added: "2.9"
options:
  id:
    description:
      - Obtain only information of the Offense with provided ID
    required: false
    type: str
  name:
    description:
      - Obtain only information of the Offense that matches the provided name
    required: true
    type: str
  status:
    description:
      - Obtain only information of Offenses of a certain status
    required: false
    choices: [ "open", "hidden", "closed" ]
    default: "open"
  assigned_to:
    description:
      - Obtain only information of Offenses assigned to a certain user
    required: false
    type: str
  closing_reason:
    description:
      - Obtain only information of Offenses that were closed by a specific closing reason
    required: false
    type: int
  closing_reason_id:
    description:
      - Obtain only information of Offenses that were closed by a specific closing reason ID
    required: false
    type: int
  follow_up:
    description:
      - Obtain only information of Offenses that are marked with the follow up flag
    required: false
    type: bool
  protected:
    description:
      - Obtain only information of Offenses that are protected
    required: false
    type: bool
notes:
  - You may provide many filters and they will all be applied, except for C(id)
    as that will return only

author: "Ansible Security Automation Team (https://github.com/ansible-security)
'''


# FIXME - provide correct example here
RETURN = '''
offenses:
  description: Information
  returned: always
  type: list
  elements: dictionaries
  contains:
    qradar_offenses:
      description: IBM QRadar Offenses found based on provided filters
      returned: always
      type: complex
      contains:
        source:
          description: Init system of the service. One of C(systemd), C(sysv), C(upstart).
          returned: always
          type: str
          sample: sysv
        state:
          description: State of the service. Either C(running), C(stopped), or C(unknown).
          returned: always
          type: str
          sample: running
        status:
          description: State of the service. Either C(enabled), C(disabled), or C(unknown).
          returned: systemd systems or RedHat/SUSE flavored sysvinit/upstart
          type: string
          sample: enabled
        name:
          description: Name of the service.
          returned: always
          type: str
          sample: arp-ethers.service
'''



EXAMPLES = '''
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_text

from ansible.module_utils.urls import Request
from ansible.module_utils.six.moves.urllib.parse import quote
from ansible.module_utils.six.moves.urllib.error import HTTPError
from ansible_collections.ansible_security.community.plugins.module_utils.qradar \
    import QRadarRequest, find_dict_in_list, set_offense_values

import copy
import json


def main():

    argspec = dict(
        id=dict(required=True, type='int'),
        name=dict(required=False, type='str'),
        assigned_to=dict(required=False, type='str'),
        closing_reason=dict(required=False, type='str'),
        closing_reason_id=dict(required=False, type='int'),
        follow_up=dict(required=False, type='bool', default=None),
        protected=dict(required=False, type='bool', default=None),
        status=dict(
            required=False,
            choices=[
                'open', 'OPEN',
                'hidden', 'HIDDEN',
                'closed', 'CLOSED'
            ],
            type='str'
        ),
    )

    module = AnsibleModule(
        argument_spec=argspec,
        #required_one_of=[
        #    ('name', 'id',),
        #],
        mutually_exclusive=[
            ('closing_reason', 'closing_reason_id',),
        ],
        supports_check_mode=True
    )

    qradar_request = QRadarRequest(
        module,
        headers={"Content-Type": "application/json", "Version": "9.1"},
        not_rest_data_keys=['name', 'id', 'assigned_to', 'closing_reason']
    )

    #if module.params['name']:
    #    # FIXME - QUERY HERE BY NAME
    #    found_offense = qradar_request.get_by_path('api/siem/offenses?filter={0}'.format(module.params['name']))

    set_offense_values(module, qradar_request)

    if module.params['id']:
        offenses = qradar_request.get_by_path('api/siem/offenses/{0}'.format(module.params['id']))

    else:

        query_strs = []

        if module.params['status']:
            query_strs.append('status={0}'.format(to_text(module.params['status'])))

        if module.params['assigned_to']:
            query_strs.append('assigned_to={0}'.format(module.params['assigned_to']))

        if module.params['closing_reason_id']:
            query_strs.append('closing_reason_id={0}'.format(module.params['closing_reason_id']))

        if module.params['follow_up'] != None:
            query_strs.append('follow_up={0}'.format(module.params['follow_up']))

        if module.params['protected'] != None:
            query_strs.append('protected={0}'.format(module.params['protected']))

        if query_strs:
            if module.check_mode:
                module.exit_json(
                    msg="A change would have been made but was not because of Check Mode.",
                    changed=True
                )

            offenses = qradar_request.get_by_path(
                'api/siem/offenses/{0}?{1}'.format(module.params['id'], '&'.join(query_strs))
            )
            #FIXME - handle the scenario in which we can search by name and this isn't a required param anymore
            module.exit_json(
                msg="Successfully updated Offense ID: {0}".format(module.params['id']),
                qradar_return_data=qradar_return_data,
                changed=True
            )
        else:
            module.exit_json(msg="No changes necessary. Nothing to do.", changed=False)
    else:
        #FIXME - handle the scenario in which we can search by name and this isn't a required param anymore
        module.fail_json(msg='Unable to find Offense ID: {0}'.format(module.params['id']))

if __name__ == '__main__':
    main()