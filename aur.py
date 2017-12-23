#!/usr/bin/env python

from ansible.module_utils.basic import *


helper_cmd = {
    'pacaur': ['env', 'LC_ALL=C', 'pacaur', '-S', '--noconfirm', '--noedit', '--needed', '--aur'],
    'trizen': ['env', 'LC_ALL=C', 'trizen', '-S', '--noconfirm', '--noedit', '--needed', '--aur'],
    'yaourt': ['env', 'LC_ALL=C', 'yaourt', '-S', '--noconfirm', '--needed'],
    'yay': ['env', 'LC_ALL=C', 'yay', '-S', '--noconfirm'],
}


def upgrade(module, helper):
    assert helper in helper_cmd

    cmd = helper_cmd[helper] + ['-u']

    rc, out, err = module.run_command(cmd, check_rc=True)

    module.exit_json(
        changed=not (out == '' or 'there is nothing to do' in out or 'No AUR update found' in out),
        msg='upgraded system',
    )


def install_packages(module, package_name, helper):
    assert helper in helper_cmd

    cmd = helper_cmd[helper] + [package_name]

    if upgrade:
        cmd += ['-u']

    rc, out, err = module.run_command(cmd, check_rc=True)

    module.exit_json(
        changed=not (out == '' or '-- skipping' in out),
        msg='installed package',
    )


def main():
    module = AnsibleModule(
        argument_spec={
            'name': {
                'required': False,
            },
            'upgrade': {
                'default': False,
                'type': 'bool',
            },
            'helper': {
                'default': 'pacaur',
                'choices': ['pacaur', 'trizen', 'yaourt', 'yay'],
            },
        },
        required_one_of=[['name', 'upgrade']],
    )

    params = module.params

    if params['upgrade'] and params['name']:
        module.fail_json(msg="Upgrade and install must be requested separately")
    if params['upgrade']:
        upgrade(module, params['helper'])
    else:
        install_packages(module, params['name'], params['helper'])


if __name__ == '__main__':
    main()
