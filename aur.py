#!/usr/bin/env python

from ansible.module_utils.basic import *
import json
from ansible.module_utils import six
from six.moves import urllib
import tarfile
import os
import os.path
import tempfile

def_lang = ['env', 'LC_ALL=C']

use_cmd = {
    'pacaur': ['pacaur', '-S', '--noconfirm', '--noedit', '--needed', '--aur'],
    'trizen': ['trizen', '-S', '--noconfirm', '--noedit', '--needed', '--aur'],
    'pikaur': ['pikaur', '-S', '--noconfirm', '--noedit', '--needed'],
    'yaourt': ['yaourt', '-S', '--noconfirm', '--needed'],
    'yay': ['yay', '-S', '--noconfirm'],
    'internal': ['makepkg', '--syncdeps', '--install', '--noconfirm', '--needed']
}


def package_installed(module, package):
    rc, _, _ = module.run_command(['pacman', '-Q', package], check_rc=False)
    return rc == 0


def install_internal(module, package):
    f = urllib.request.urlopen('https://aur.archlinux.org/rpc/?v=5&type=info&arg={}'.format(package))
    result = json.loads(f.read().decode('utf8'))
    if result['resultcount'] != 1:
        return (1, '', 'package not found')
    result = result['results'][0]
    f = urllib.request.urlopen('https://aur.archlinux.org/{}'.format(result['URLPath']))
    current_path = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        tar_file = '{}.tar.gz'.format(result['Name'])
        with open(tar_file, 'wb') as out:
            out.write(f.read())
        tar = tarfile.open(tar_file)
        tar.extractall()
        tar.close()
        os.chdir(format(result['Name']))
        rc, out, err = module.run_command(use_cmd['internal'], check_rc=True)
        os.chdir(current_path)
    return (rc, out, err)


def upgrade(module, use):
    assert use in use_cmd

    rc, out, err = module.run_command(def_lang + use_cmd[use] + ['-u'], check_rc=True)

    module.exit_json(
        changed=not (out == '' or 'there is nothing to do' in out or 'No AUR updates found' in out),
        msg='upgraded system',
        helper_used=use,
    )


def install_packages(module, packages, use, skip_installed):
    assert use in use_cmd

    changed_iter = False

    for package in packages:
        if skip_installed:
            if package_installed(module, package):
                rc = 0
                continue
        if use == 'internal':
            rc, out, err = install_internal(module, package)
        else:
            rc, out, err = module.run_command(def_lang + use_cmd[use] + [package], check_rc=True)
        changed_iter = changed_iter or not (out == '' or '-- skipping' in out or 'there is nothing to do' in out)

    module.exit_json(
        changed=changed_iter,
        msg='installed package' if not rc else err,
        helper_used=use,
        rc=rc,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            'name': {
                'type': 'list',
            },
            'upgrade': {
                'default': False,
                'type': 'bool',
            },
            'use': {
                'default': 'auto',
                'choices': ['auto', 'pacaur', 'trizen', 'pikaur', 'yaourt', 'yay', 'internal'],
            },
            'skip_installed': {
                'default': 'no',
                'type': 'bool',
            },
        },
        required_one_of=[['name', 'upgrade']],
    )

    params = module.params

    if params['use'] == 'auto':
        use = 'internal'
        for k in use_cmd:
            if module.get_bin_path(k, False):
                use = k
                break
    else:
        use = params['use']

    if params['upgrade'] and (params['name'] or params['skip_installed'] or use == 'internal'):
        module.fail_json(msg="Upgrade cannot be used with this option.")
    else:
        if params['upgrade']:
            upgrade(module, use)
        else:
            install_packages(module, params['name'], use, params['skip_installed'])


if __name__ == '__main__':
    main()
