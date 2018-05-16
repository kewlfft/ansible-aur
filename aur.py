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
    'aurman': ['aurman', '-S', '--noconfirm', '--noedit', '--needed'],
    'pacaur': ['pacaur', '-S', '--noconfirm', '--noedit', '--needed'],
    'trizen': ['trizen', '-S', '--noconfirm', '--noedit', '--needed'],
    'pikaur': ['pikaur', '-S', '--noconfirm', '--noedit', '--needed'],
    'yaourt': ['yaourt', '-S', '--noconfirm', '--needed'],
    'yay': ['yay', '-S', '--noconfirm'],
    'makepkg': ['makepkg', '--syncdeps', '--install', '--noconfirm', '--needed']
}
# optional: aurman, pacaur, trizen have a --aur option, do things only for aur


def package_installed(module, package):
    rc, _, _ = module.run_command(['pacman', '-Q', package], check_rc=False)
    return rc == 0


def check_packages(module, packages):
    """
    Inform the user what would change if the module were run
    """
    would_be_changed = []

    for package in packages:
        installed = package_installed(module, package)
        if not installed:
            would_be_changed.append(package)

    if would_be_changed:
        status = True
        if (len(packages) > 1):
            message = '%s package(s) would be installed' % str(len(would_be_changed))
        else:
            message = 'package would be installed'
    else:
        status = False
        if (len(packages) > 1):
            message = 'all packages are already installed'
        else:
            message = 'package is already installed'
    module.exit_json(changed=status, msg=message)


def install_with_makepkg(module, package):
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
        if module.params['skip_pgp_check']:
            use_cmd['makepkg'].append('--skippgpcheck')
        rc, out, err = module.run_command(use_cmd['makepkg'], check_rc=True)
        os.chdir(current_path)
    return (rc, out, err)


def upgrade(module, use):
    assert use in use_cmd

    rc, out, err = module.run_command(def_lang + use_cmd[use] + ['-u'], check_rc=True)

    module.exit_json(
        changed=not (out == '' or 'nothing to do' in out or 'No AUR updates found' in out),
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
        if use == 'makepkg':
            rc, out, err = install_with_makepkg(module, package)
        else:
            rc, out, err = module.run_command(def_lang + use_cmd[use] + [package], check_rc=True)
        changed_iter = changed_iter or not (out == '' or '-- skipping' in out or 'nothing to do' in out)

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
                'choices': ['auto', 'aurman', 'pacaur', 'trizen', 'pikaur', 'yaourt', 'yay', 'makepkg'],
            },
            'skip_installed': {
                'default': False,
                'type': 'bool',
            },
            'skip_pgp_check': {
                'default': False,
                'type': 'bool',
            },
        },
        required_one_of=[['name', 'upgrade']],
        supports_check_mode=True
    )

    params = module.params

    if module.check_mode:
        check_packages(module, params['name'])

    if params['use'] == 'auto':
        use = 'makepkg'
        # auto: select the first helper for which the bin is found
        for k in use_cmd:
            if module.get_bin_path(k, False):
                use = k
                break
    else:
        use = params['use']

    if params['upgrade'] and (params['name'] or params['skip_installed'] or use == 'makepkg'):
        module.fail_json(msg="Upgrade cannot be used with this option.")
    else:
        if params['upgrade']:
            upgrade(module, use)
        else:
            install_packages(module, params['name'], use, params['skip_installed'])


if __name__ == '__main__':
    main()
