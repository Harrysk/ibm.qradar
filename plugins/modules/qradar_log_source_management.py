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
module: qradar_log_source_management
short_description: Manage Log Sources in QRadar
description:
  - This module allows for addition, deletion, or modification of Log Sources in QRadar
version_added: "2.9"
options:
  name:
    description:
     - Name of Log Source
    required: true
    type: str
  state:
    description:
      - Add or remove a log source.
    required: true
    choices: [ "present", "absent" ]
  type_name:
    description:
      - Type of resource by name
    required: false
    type: str
  type_id:
    description:
      - Type of resource by type_id
    required: false
    type: int
  identifier:
    description:
      - Log Source Identifier (Typically IP Address or Hostname of log source)
    required: true
    type: str
  description:
    description:
      - Description of log source
    required: true
    type: str

notes:
  - Either C(type) or C(type_id) is required

author: "Ansible Security Automation Team (https://github.com/ansible-security)
'''

EXAMPLES = '''
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_text

from ansible.module_utils.urls import Request
from ansible.module_utils.six.moves.urllib.parse import quote
from ansible.module_utils.six.moves.urllib.error import HTTPError
from ansible_collections.ibm.qradar.module_utils.qradar import QRadarRequest, find_dict_in_list

import json

def set_log_source_values(module, qradar_request):
    if module.params['type_name']:
        log_source_type_found = qradar_request.get_by_path(
            'api/config/event_sources/log_source_management/log_source_types?filter={0}'.format(
                quote('name="{0}"'.format(module.params['type_name']))
            )
        )[0]
    if module.params['type_id']:
        log_source_type_found = qradar_request.get_by_path(
            'api/config/event_sources/log_source_management/log_source_types?filter={0}'.format(
                quote('id="{0}"'.format(module.params['type_id']))
            )
        )[0]
    if log_source_type_found:
        if not module.params['type_id']:
            module.params['type_id'] = log_source_type_found['id']
    else:
        module.fail_json(msg="Incompatible type provided, please consult QRadar Documentation for Log Source Types")

    if module.params['protocol_type_id']:
        found_dict_in_list, _fdil_index = find_dict_in_list(
            log_source_type_found['protocol_types'],
            'protocol_id', module.params['protocol_type_id']
        )
        if not found_dict_in_list:
            module.fail_json(
                msg="Incompatible protocol_type_id provided, please consult QRadar Documentation for Log Source Types"
            )
    else:
        # Set it to the default as provided by the QRadar Instance
        module.params['protocol_type_id'] = log_source_type_found['protocol_types'][0]['protocol_id']

    module.params['protocol_parameters'] = [
        {
            'id': module.params['protocol_type_id'],
            'name': 'identifier',
            'value': module.params['identifier'],
        },
    ]


def main():

    argspec = dict(
        name=dict(required=True, type='str'),
        state=dict(choices=['present', 'absent'], required=True),
        type_name=dict(required=False, type='str'),
        type_id=dict(required=False, type='str'),
        identifier=dict(required=True, type='str'),
        protocol_type_id=dict(required=False, type='int'),
        description=dict(required=True, type='str'),
    )

    module = AnsibleModule(
        argument_spec=argspec,
        required_one_of=[
            ('type_name', 'type_id',),
        ],
        mutually_exclusive=[
            ('type_name', 'type_id',),
        ],
        supports_check_mode=True
    )

    qradar_request = QRadarRequest(
        module,
        headers={"Content-Type": "application/json", "Version": "9.1"},
        not_rest_data_keys=['state', 'type_name', 'identifier']
    )

    log_source_exists = qradar_request.get_by_path(
            'api/config/event_sources/log_source_management/log_sources?filter={0}'.format(
                quote('name="{0}"'.format(module.params['name']))
        )
    )

    if log_source_exists:

        if module.params['state'] == 'present':
            existing_log_source_protocol_identifier, _elspi_index = find_dict_in_list(
                log_source_exists[0]['protocol_parameters'],
                'name',
                'identifier'
            )

            set_log_source_values(module, qradar_request)

            comparison_map = [
                existing_log_source_protocol_identifier['value'] == module.params['identifier'],
                log_source_exists[0]['name'] == module.params['name'],
                log_source_exists[0]['type_id'] == module.params['type_id'],
                to_text(log_source_exists[0]['description']) == to_text(module.params['description'])
            ]

            if all(comparison_map):
                module.exit_json(changed=False, msg="Nothing to do.")
            else:
                log_source_exists[0]['protocol_parameters'][_elspi_index] = module.params['protocol_parameters'][0]
                log_source_exists[0]['name'] = module.params['name']
                log_source_exists[0]['type_id'] = module.params['type_id']
                log_source_exists[0]['description'] = module.params['description']
                if module.check_mode:
                    qradar_return_data = {"EMPTY": "IN CHECK MODE, NO TRANSACTION TOOK PLACE"}
                else:
                    qradar_return_data = qradar_request.create_update(
                        'api/config/event_sources/log_source_management/log_sources',
                        data=json.dumps(log_source_exists)
                    )

                module.exit_json(
                    msg="Successfully updated log source: {0}".format(module.params['name']),
                    qradar_return_data=qradar_return_data,
                    changed=True
                )

        if module.params['state'] == 'absent':
            if module.check_mode:
                qradar_return_data = {"EMPTY": "IN CHECK MODE, NO TRANSACTION TOOK PLACE"}
            else:
                qradar_return_data = qradar_request.delete_by_path(
                    'api/config/event_sources/log_source_management/log_sources/{0}'.format(log_source_exists[0]['id'])
                )

            module.exit_json(
                msg="Successfully deleted log source: {0}".format(module.params['name']),
                qradar_return_data=qradar_return_data,
                changed=True
            )
    else:
        if module.params['state'] == 'present':
            set_log_source_values(module, qradar_request)
            if module.check_mode:
                qradar_return_data = {"EMPTY": "IN CHECK MODE, NO TRANSACTION TOOK PLACE"}
            else:
                qradar_return_data = qradar_request.create_update(
                    'api/config/event_sources/log_source_management/log_sources',
                    data=json.dumps([qradar_request.get_data()])
                )

            module.exit_json(
                msg="Successfully created log source: {0}".format(module.params['name']),
                qradar_return_data=qradar_return_data,
                changed=True
            )

        if module.params['state'] == 'absent':
            module.exit_json(changed=False, msg="Nothing to do.")

if __name__ == '__main__':
    main()
