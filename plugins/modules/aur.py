#!/usr/bin/python

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url
import json
import shlex
import tarfile
import os
import os.path
import shutil
import tempfile
import urllib.parse


DOCUMENTATION = '''
---
module: aur
short_description: Manage packages from the AUR
description:
    - Manage packages from the Arch User Repository (AUR)
author:
    - Kewl <xrjy@nygb.rh.bet(rot13)>
options:
    name:
        description:
            - Name or list of names of the package(s) to install or upgrade.

    state:
        description:
            - Desired state of the package.
        default: present
        choices: [ present, latest ]

    upgrade:
        description:
            - Whether or not to upgrade whole system.
        default: no
        type: bool

    update_cache:
        description:
            - Whether or not to update_cache the package cache.
        default: no
        type: bool

    use:
        description:
            - The tool to use, 'auto' uses the first known helper found and makepkg as a fallback.
        default: auto
        choices: [ auto, yay, paru, pacaur, trizen, pikaur, aurman, makepkg ]

    extra_args:
        description:
            - Arguments to pass to the tool.
              Requires that the 'use' option be set to something other than 'auto'.
        type: str

    skip_pgp_check:
        description:
            - Only valid with makepkg.
              Skip PGP signatures verification of source file.
              This is useful when installing packages without GnuPG (properly) configured.
              Cannot be used unless use is set to 'makepkg'.
        type: bool
        default: no

    ignore_arch:
        description:
            - Only valid with makepkg.
              Ignore a missing or incomplete arch field, useful when the PKGBUILD does not have the arch=('yourarch') field.
              Cannot be used unless use is set to 'makepkg'.
        type: bool
        default: no

    aur_only:
        description:
            - Limit helper operation to the AUR.
        type: bool
        default: no

    local_pkgbuild:
        description:
            - Only valid with makepkg or pikaur.
              Directory with PKGBUILD and build files.
              Cannot be used unless use is set to 'makepkg' or 'pikaur'.
        type: path
        default: no
notes:
  - When used with a `loop:` each package will be processed individually,
    it is much more efficient to pass the list directly to the `name` option.
'''

RETURN = '''
msg:
    description: action that has been taken
helper:
    description: the helper that was actually used
'''

EXAMPLES = '''
- name: Install trizen using makepkg, skip if trizen is already installed
  aur: name=trizen use=makepkg state=present
  become: yes
  become_user: aur_builder
'''

def_lang = ['env', 'LC_ALL=C', 'LANGUAGE=C']

use_cmd = {
    'yay': ['yay', '-S', '--noconfirm', '--needed', '--cleanafter'],
    'paru': ['paru', '-S', '--noconfirm', '--needed', '--cleanafter'],
    'pacaur': ['pacaur', '-S', '--noconfirm', '--noedit', '--needed'],
    'trizen': ['trizen', '-S', '--noconfirm', '--noedit', '--needed'],
    'pikaur': ['pikaur', '-S', '--noconfirm', '--noedit', '--needed'],
    'aurman': ['aurman', '-S', '--noconfirm', '--noedit', '--needed', '--skip_news', '--pgp_fetch', '--skip_new_locations'],
    'makepkg': ['makepkg', '--syncdeps', '--install', '--noconfirm', '--needed']
}

use_cmd_local_pkgbuild = {
    'pikaur': ['pikaur', '-P', '--noconfirm', '--noedit', '--needed', '--install'],
    'makepkg': ['makepkg', '--syncdeps', '--install', '--noconfirm', '--needed']
}

has_aur_option = ['yay', 'paru', 'pacaur', 'trizen', 'pikaur', 'aurman']


def package_installed(module, package):
    """
    Determine if the package is already installed
    """
    rc, _, _ = module.run_command(['pacman', '-Q', package], check_rc=False)
    return rc == 0


def check_packages(module, packages):
    """
    Inform the user what would change if the module were run
    """
    would_be_changed = [package for package in packages if not package_installed(module, package)]
    diff = {'before': '', 'after': '\n'.join(package for package in would_be_changed if module._diff)}

    if would_be_changed:
        status = True
        if len(packages) > 1:
            message = '{} package(s) would be installed'.format(len(would_be_changed))
        else:
            message = 'package would be installed'
    else:
        status = False
        if len(packages) > 1:
            message = 'all packages are already installed'
        else:
            message = 'package is already installed'
    module.exit_json(changed=status, msg=message, diff=diff)


def build_command_prefix(use, extra_args, skip_pgp_check=False, ignore_arch=False, aur_only=False, local_pkgbuild=None, update_cache=False):
    """
    Create the prefix of a command that can be used by the install and upgrade functions.
    """
    if local_pkgbuild:
        command = def_lang + use_cmd_local_pkgbuild[use]
    else:
        command = def_lang + use_cmd[use]
    if skip_pgp_check:
        command.append('--skippgpcheck')
    if ignore_arch:
        command.append('--ignorearch')
    if aur_only and use in has_aur_option:
        command.append('--aur')
    if local_pkgbuild and use != 'makepkg':
        command.append(local_pkgbuild)
    if update_cache:
        command.append('-y')
    if extra_args:
        command += shlex.split(extra_args)
    return command


def install_with_makepkg(module, package, extra_args, skip_pgp_check, ignore_arch, local_pkgbuild=None):
    """
    Install the specified package or a local PKGBUILD with makepkg
    """
    if not local_pkgbuild:
        module.get_bin_path('fakeroot', required=True)
        f = open_url('https://aur.archlinux.org/rpc/?v=5&type=info&arg={}'.format(urllib.parse.quote(package)))
        result = json.loads(f.read().decode('utf8'))
        if result['resultcount'] != 1:
            return (1, '', 'package {} not found'.format(package))
        result = result['results'][0]
        f = open_url('https://aur.archlinux.org/{}'.format(result['URLPath']))
    with tempfile.TemporaryDirectory() as tmpdir:
        if local_pkgbuild:
            shutil.copytree(local_pkgbuild, tmpdir, dirs_exist_ok=True)
            command = build_command_prefix('makepkg', extra_args)
            rc, out, err = module.run_command(command, cwd=tmpdir, check_rc=True)
        else:
            tar = tarfile.open(mode='r|*', fileobj=f)
            tar.extractall(tmpdir)
            tar.close()
            command = build_command_prefix('makepkg', extra_args, skip_pgp_check=skip_pgp_check, ignore_arch=ignore_arch)
            rc, out, err = module.run_command(command, cwd=os.path.join(tmpdir, result['Name']), check_rc=True)
    return (rc, out, err)


def install_local_package(module, package, use, extra_args, local_pkgbuild):
    """
    Install the specified package with a local PKGBUILD
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        shutil.copytree(local_pkgbuild, tmpdir, dirs_exist_ok=True)
        command = build_command_prefix(use, extra_args, local_pkgbuild=tmpdir + '/PKGBUILD')
        rc, out, err = module.run_command(command, check_rc=True)
    return (rc, out, err)


def check_upgrade(module, use):
    """
    Inform user how many packages would be upgraded
    """
    rc, stdout, stderr = module.run_command([use, '-Qu'], check_rc=True)
    num_packages = sum(1 for line in stdout.splitlines() if line.strip())
    module.exit_json(
        changed=num_packages > 0,
        msg=f"{num_packages} package(s) would be upgraded",
        helper=use,
    )


def upgrade(module, use, extra_args, aur_only, update_cache):
    """
    Upgrade the whole system
    """
    assert use in use_cmd

    command = build_command_prefix(use, extra_args, aur_only=aur_only, update_cache=update_cache)
    command.append('-u')

    rc, out, err = module.run_command(command, check_rc=True)

    module.exit_json(
        changed=not (out == '' or 'nothing to do' in out.lower() or 'No AUR updates found' in out),
        msg='upgraded system',
        helper=use,
    )


def install_packages(module, packages, use, extra_args, state, skip_pgp_check, ignore_arch, aur_only, local_pkgbuild, update_cache):
    """
    Install the specified packages
    """
    if local_pkgbuild:
        assert use in use_cmd_local_pkgbuild
    else:
        assert use in use_cmd

    changed_iter = False

    for package in packages:
        if state == 'present' and package_installed(module, package):
            rc = 0
            continue
        if use == 'makepkg':
            rc, out, err = install_with_makepkg(module, package, extra_args, skip_pgp_check, ignore_arch, local_pkgbuild)
        elif local_pkgbuild:
            rc, out, err = install_local_package(module, package, use, extra_args, local_pkgbuild)
        else:
            command = build_command_prefix(use, extra_args, aur_only=aur_only, update_cache=update_cache)
            command.append(package)
            rc, out, err = module.run_command(command, check_rc=True)

        changed_iter |= not (out == '' or 'up-to-date -- skipping' in out or 'nothing to do' in out.lower())

    message = 'installed package(s)' if changed_iter else 'package(s) already installed'

    module.exit_json(
        changed=changed_iter,
        msg=message if not rc else err,
        helper=use,
        rc=rc,
    )


def make_module():
    module = AnsibleModule(
        argument_spec={
            'name': {
                'type': 'list',
            },
            'state': {
                'default': 'present',
                'choices': ['present', 'latest'],
            },
            'upgrade': {
                'type': 'bool',
            },
            'update_cache': {
                'default': False,
                'type': 'bool',
            },
            'use': {
                'default': 'auto',
                'choices': ['auto'] + list(use_cmd.keys()),
            },
            'extra_args': {
                'default': None,
                'type': 'str',
            },
            'skip_pgp_check': {
                'default': False,
                'type': 'bool',
            },
            'ignore_arch': {
                'default': False,
                'type': 'bool',
            },
            'aur_only': {
                'default': False,
                'type': 'bool',
            },
            'local_pkgbuild': {
                'default': None,
                'type': 'path',
            },
        },
        mutually_exclusive=[['name', 'upgrade']],
        required_one_of=[['name', 'upgrade']],
        supports_check_mode=True
    )

    params = module.params

    use = params['use']

    if params['name'] == []:
        module.fail_json(msg="'name' cannot be empty.")

    if use == 'auto':
        if params['extra_args'] is not None:
            module.fail_json(msg="'extra_args' cannot be used with 'auto', a tool must be specified.")
        use = 'makepkg'
        # auto: select the first helper for which the bin is found
        for k in use_cmd:
            if module.get_bin_path(k):
                use = k
                break

    if use != 'makepkg' and (params['skip_pgp_check'] or params['ignore_arch']):
        module.fail_json(msg="This option is only available with 'makepkg'.")

    if not (use in use_cmd_local_pkgbuild) and params['local_pkgbuild']:
        module.fail_json(msg="This option is not available with '%s'" % use)

    if params['local_pkgbuild'] and not os.path.isdir(params['local_pkgbuild']):
        module.fail_json(msg="Directory %s not found" % (params['local_pkgbuild']))

    if params['local_pkgbuild'] and not os.access(params['local_pkgbuild'] + '/PKGBUILD', os.R_OK):
        module.fail_json(msg="PKGBUILD inside %s not readable" % (params['local_pkgbuild']))

    if params.get('upgrade', False) and use == 'makepkg':
        module.fail_json(msg="The 'upgrade' action cannot be used with 'makepkg'.")

    return module, use


def apply_module(module, use):
    params = module.params

    if params.get('upgrade', False):
        if module.check_mode:
            check_upgrade(module, use)
        else:
            upgrade(module, use, params['extra_args'], params['aur_only'], params['update_cache'])
    else:
        if module.check_mode:
            check_packages(module, params['name'])
        else:
            install_packages(module,
                             params['name'],
                             use,
                             params['extra_args'],
                             params['state'],
                             params['skip_pgp_check'],
                             params['ignore_arch'],
                             params['aur_only'],
                             params['local_pkgbuild'],
                             params['update_cache'])


def main():
    module, use = make_module()
    apply_module(module, use)


if __name__ == '__main__':
    main()
