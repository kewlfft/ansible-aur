#!/usr/bin/env python3

import json
import tarfile
import tempfile
import unittest
from unittest.mock import patch, MagicMock, Mock

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes

import aur


def Any(cls):
    '''
    Return an instance of a class that extends the given type and compares as
    equal to anything thrown at it.
    This is useful when making assertions about how a mock method was invoked
    when you only care to constrain a subset of function parameters.
    '''
    class Any(cls):
        def __eq__(self, other):
            return True

    return Any()


class AnsibleExitJson(Exception):
    '''
    Raised by the mocked function AnsibleModule.exit_json.
    Used to terminate control-flow tested functions.
    '''
    pass


class AnsibleFailJson(Exception):
    '''
    Raised by the mocked function AnsibleModule.fail_json.
    Used to terminate control-flow tested functions.
    '''
    pass


def exit_json(*args, **kwargs):
    '''
    Package kwargs into an exception and raise to terminate control-flow.
    '''
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):
    '''
    Package kwargs into an exception and raise to terminate control-flow.
    '''
    raise AnsibleFailJson(kwargs)


class MockedFunctionArgumentError(Exception):
    '''
    Raised by MatchFnArgs.__call__ when provided arguments do not match.
    '''
    def __init__(self, expected, actual):
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return '\nexpected: {} {}\n  actual: {} {}'.format(
            str(self.expected[0]),
            str(self.expected[1]),
            str(self.actual[0]),
            str(self.actual[1]),
        )


class MatchFnArgs:
    '''
    A callable object that will match arguments provided at instantiation to
    those provided at invocation.
    '''
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        if self.args != args or self.kwargs != kwargs:
            raise MockedFunctionArgumentError(
                expected=(self.args, self.kwargs),
                actual=(args, kwargs),
            )


class MatchCall:
    '''
    A callable object that matches provided arguments, raises a potential
    exception, and returns a specific value.
    '''
    def __init__(self, match_args, return_value=None, exception=None):
        self.match_args = match_args
        self.return_value = return_value
        self.exception = exception

    def __call__(self, *args, **kwargs):
        self.match_args(*args, **kwargs)
        if self.exception:
            raise self.exception
        return self.return_value


class IterativeMatchCall:
    '''
    A callable object that matches a series of calls, invoking the next provided
    side-effect each call.
    '''
    def __init__(self, side_effects):
        self.side_effects = side_effects
        self.side_effect = iter(self.side_effects)

    def __call__(self, *args, **kwargs):
        return next(self.side_effect)(*args, **kwargs)


class AurModuleInvalidParamsTest(unittest.TestCase):
    def setUp(self):
        # Patch the two terminal module methods here so we can avoid repetition
        # in every test case.
        self.exit_json = patch.object(aur.AnsibleModule, 'exit_json', exit_json)
        self.fail_json = patch.object(aur.AnsibleModule, 'fail_json', fail_json)
        self.exit_json.start()
        self.fail_json.start()

    def tearDown(self):
        self.exit_json.stop()
        self.fail_json.stop()

    def set_module_args(self, args):
        args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
        basic._ANSIBLE_ARGS = to_bytes(args)

    def test_empty(self):
        with self.assertRaises(AnsibleFailJson):
            self.set_module_args({})
            aur.make_module()

    @patch.object(aur.AnsibleModule, 'get_bin_path')
    def test_name_and_upgrade(self, get_bin_path):
        with self.assertRaises(AnsibleFailJson):
            self.set_module_args({
                'name': ['ansible'],
                'upgrade': True,
            })
            aur.make_module()
        get_bin_path.assert_not_called()

    @patch.object(aur.AnsibleModule, 'get_bin_path')
    def test_bad_helper(self, get_bin_path):
        with self.assertRaises(AnsibleFailJson):
            self.set_module_args({
                'name': ['ansible'],
                'use': 'doesnotexist',
            })
            aur.make_module()
        get_bin_path.assert_not_called()

    @patch.object(aur.AnsibleModule, 'get_bin_path')
    def test_extra_args_without_use(self, get_bin_path):
        with self.assertRaises(AnsibleFailJson) as cm:
            self.set_module_args({
                'name': ['ansible'],
                'extra_args': 'custom-arg',
            })
            aur.make_module()
        get_bin_path.assert_not_called()

    @patch.object(aur.AnsibleModule, 'get_bin_path')
    def test_extra_args_with_auto_use(self, get_bin_path):
        with self.assertRaises(AnsibleFailJson) as cm:
            self.set_module_args({
                'name': ['ansible'],
                'use': 'auto',
                'extra_args': 'custom-arg',
            })
            aur.make_module()
        get_bin_path.assert_not_called()

    @patch.object(aur.AnsibleModule, 'get_bin_path')
    def test_upgrade_with_makepkg_use(self, get_bin_path):
        get_bin_path.return_value = False
        with self.assertRaises(AnsibleFailJson) as cm:
            self.set_module_args({
                'upgrade': True,
                'use': 'makepkg',
            })
            aur.make_module()
        get_bin_path.assert_not_called()


class AurModuleApplyTest(unittest.TestCase):
    def setUp(self):
        self.module = MagicMock()
        self.module.check_mode = False
        self.module._diff = False
        self.module.exit_json.side_effect = exit_json
        self.module.fail_json.side_effect = fail_json

        self.ansible_module = patch(
            'aur.AnsibleModule',
            return_value=self.module,
        )
        self.ansible_module.start()

    def tearDown(self):
        self.ansible_module.stop()


class AurModuleApplyCheckTest(AurModuleApplyTest):
    def test_check_installed(self):
        self.module.check_mode = True
        self.module.params = {'name': ['ansible']}
        self.module.run_command.return_value = (0, '', '')

        with self.assertRaises(AnsibleExitJson):
            aur.apply_module(aur.AnsibleModule(), 'makepkg')

        self.module.run_command.assert_called_once_with(
            ['pacman', '-Q', 'ansible'],
            check_rc=False,
        )
        self.module.exit_json.assert_called_once_with(
            changed=False,
            diff=Any(dict),
            msg=Any(str),
        )
        self.module.fail_json.assert_not_called()

    def test_check_not_installed(self):
        self.module.check_mode = True
        self.module.params = {'name': ['ansible']}
        self.module.run_command.return_value = (1, '', '')

        with self.assertRaises(AnsibleExitJson):
            aur.apply_module(aur.AnsibleModule(), 'makepkg')

        self.module.run_command.assert_called_once_with(
            ['pacman', '-Q', 'ansible'],
            check_rc=False,
        )
        self.module.exit_json.assert_called_once_with(
            changed=True,
            diff=Any(dict),
            msg=Any(str),
        )
        self.module.fail_json.assert_not_called()


class AurModuleApplyUpgradeTest(AurModuleApplyTest):
    def test_upgrade_no_change(self):
        use = 'yay'
        extra_args = None

        self.module.params = {
            'upgrade': True,
            'extra_args': extra_args,
            'aur_only': False,
        }
        self.module.run_command.return_value = (0, '', '')

        with self.assertRaises(AnsibleExitJson):
            aur.apply_module(aur.AnsibleModule(), use)

        self.module.run_command.assert_called_once_with(
            aur.build_command_prefix(use, extra_args) + ['-u'],
            check_rc=True,
        )
        self.module.exit_json.assert_called_once_with(
            changed=False,
            helper=use,
            msg=Any(str),
        )
        self.module.fail_json.assert_not_called()

    def test_upgrade_change(self):
        use = 'yay'
        extra_args = None

        self.module.params = {
            'upgrade': True,
            'extra_args': extra_args,
            'aur_only': False,
        }
        self.module.run_command.return_value = (0, 'something happened', '')

        with self.assertRaises(AnsibleExitJson):
            aur.apply_module(aur.AnsibleModule(), use)

        self.module.run_command.assert_called_once_with(
            aur.build_command_prefix(use, extra_args) + ['-u'],
            check_rc=True,
        )
        self.module.exit_json.assert_called_once_with(
            changed=True,
            helper=use,
            msg=Any(str),
        )
        self.module.fail_json.assert_not_called()


class AurModuleApplyInstallTest(AurModuleApplyTest):
    def setUp(self):
        super().setUp()
        self.close_on_teardown = []

    def tearDown(self):
        super().tearDown()
        for element in self.close_on_teardown:
            element.close()

    def test_install_present_package(self):
        use = 'yay'
        extra_args = None

        self.module.params = {
            'name': ['ansible'],
            'state': 'present',
            'extra_args': extra_args,
            'skip_pgp_check': False,
            'ignore_arch': False,
            'aur_only': False,
        }
        self.module.run_command.return_value = (0, '', '')

        with self.assertRaises(AnsibleExitJson):
            aur.apply_module(aur.AnsibleModule(), use)

        self.module.run_command.assert_called_once_with(
            ['pacman', '-Q', 'ansible'],
            check_rc=False,
        )
        self.module.exit_json.assert_called_once_with(
            changed=False,
            msg=Any(str),
            helper=use,
            rc=0,
        )
        self.module.fail_json.assert_not_called()

    def test_install_absent_package_success(self):
        use = 'yay'
        extra_args = None

        self.module.params = {
            'name': ['ansible'],
            'state': 'present',
            'extra_args': extra_args,
            'skip_pgp_check': False,
            'ignore_arch': False,
            'aur_only': False,
        }
        self.module.run_command.side_effect = IterativeMatchCall([
            MatchCall(
                MatchFnArgs(['pacman', '-Q', 'ansible'], check_rc=False),
                return_value=(1, '', ''),
            ),
            MatchCall(
                MatchFnArgs(
                    aur.build_command_prefix(use, extra_args) + ['ansible'],
                    check_rc=True,
                ),
                return_value=(0, 'something happened', ''),
            ),
        ])

        with self.assertRaises(AnsibleExitJson):
            aur.apply_module(aur.AnsibleModule(), use)

        self.module.run_command.assert_called()
        self.module.exit_json.assert_called_once_with(
            changed=True,
            msg=Any(str),
            helper=use,
            rc=0,
        )
        self.module.fail_json.assert_not_called()

    def test_install_absent_package_failure(self):
        use = 'yay'
        extra_args = None

        self.module.params = {
            'name': ['ansible'],
            'state': 'present',
            'extra_args': extra_args,
            'skip_pgp_check': False,
            'ignore_arch': False,
            'aur_only': False,
        }
        self.module.run_command.side_effect = IterativeMatchCall([
            MatchCall(
                MatchFnArgs(['pacman', '-Q', 'ansible'], check_rc=False),
                return_value=(1, '', ''),
            ),
            MatchCall(
                MatchFnArgs(
                    aur.build_command_prefix(use, extra_args) + ['ansible'],
                    check_rc=True,
                ),
                return_value=(1, '', ''),
            ),
        ])

        with self.assertRaises(AnsibleExitJson):
            aur.apply_module(aur.AnsibleModule(), use)

        self.module.run_command.assert_called()
        self.module.exit_json.assert_called_once_with(
            changed=False,
            msg=Any(str),
            helper=use,
            rc=1,
        )
        self.module.fail_json.assert_not_called()

    def test_install_absent_package_extra_args_yay(self):
        use = 'yay'
        extra_args = 'custom-arg'

        self.module.params = {
            'name': ['ansible'],
            'state': 'present',
            'extra_args': extra_args,
            'skip_pgp_check': False,
            'ignore_arch': False,
            'aur_only': False,
        }
        self.module.run_command.side_effect = IterativeMatchCall([
            MatchCall(
                MatchFnArgs(['pacman', '-Q', 'ansible'], check_rc=False),
                return_value=(1, '', ''),
            ),
            MatchCall(
                MatchFnArgs(
                    # Explicitly append extra_args instead of passing it to
                    # build_command_prefix() so we can be sure that our args are
                    # begin included.
                    aur.build_command_prefix(use, []) + [extra_args, 'ansible'],
                    check_rc=True,
                ),
                return_value=(0, 'something happened', ''),
            ),
        ])

        with self.assertRaises(AnsibleExitJson):
            aur.apply_module(aur.AnsibleModule(), use)

        self.module.run_command.assert_called()
        self.module.exit_json.assert_called_once_with(
            changed=True,
            msg=Any(str),
            helper=use,
            rc=0,
        )
        self.module.fail_json.assert_not_called()

    @patch('aur.open_url')
    def test_install_absent_package_extra_args_makepkg(self, open_url):
        use = 'makepkg'
        extra_args = 'custom-arg'

        # Populate a tempfile with a JSON-serialized response of querying for a
        # package by name.
        find_url_response = {
            'resultcount': 1,
            'results': [
                {
                    'URLPath': 'url-path',
                    'Name': 'ansible',
                },
            ],
        }
        find_url_tempfile = tempfile.TemporaryFile(mode='w+b')
        self.close_on_teardown.append(find_url_tempfile)
        find_url_tempfile.write(json.dumps(find_url_response).encode('utf-8'))
        find_url_tempfile.seek(0)

        # Populate a tempfile with the contents of an empty tarfile.
        download_file_tempfile = tempfile.TemporaryFile('w+b')
        self.close_on_teardown.append(download_file_tempfile)
        tarfile.open(mode='w', fileobj=download_file_tempfile).close()
        download_file_tempfile.seek(0)

        self.module.params = {
            'name': ['ansible'],
            'state': 'present',
            'extra_args': extra_args,
            'skip_pgp_check': False,
            'ignore_arch': False,
            'aur_only': False,
        }
        open_url.side_effect = IterativeMatchCall([
            MatchCall(
                MatchFnArgs(aur.find_package_url('ansible')),
                return_value=find_url_tempfile,
            ),
            MatchCall(
                MatchFnArgs(aur.download_package_url('url-path')),
                return_value=download_file_tempfile,
            ),
        ])
        self.module.run_command.side_effect = IterativeMatchCall([
            MatchCall(
                MatchFnArgs(['pacman', '-Q', 'ansible'], check_rc=False),
                return_value=(1, '', ''),
            ),
            MatchCall(
                MatchFnArgs(
                    # Explicitly append extra_args instead of passing it to
                    # build_command_prefix() so we can be sure that our args are
                    # begin included.
                    aur.build_command_prefix(use, []) + [extra_args],
                    cwd=Any(str),
                    check_rc=True,
                ),
                return_value=(0, 'something happened', ''),
            ),
        ])

        with self.assertRaises(AnsibleExitJson):
            aur.apply_module(aur.AnsibleModule(), use)

        open_url.assert_called()
        self.module.run_command.assert_called()
        self.module.exit_json.assert_called_once_with(
            changed=True,
            msg=Any(str),
            helper=use,
            rc=0,
        )
        self.module.fail_json.assert_not_called()


if __name__ == '__main__':
    unittest.main()
