# Ansible Collection - kewlfft.aur

## Description

This collection includes an Ansible module to manage packages from the AUR.

## Installation

### Install the `kewlfft.aur` collection from Ansible Galaxy

To install this collection from Ansible Galaxy, run the following command:

```shell
ansible-galaxy collection install kewlfft.aur
```

Alternatively, you can include the collection in a `requirements.yml` file and then run `ansible-galaxy collection install -r requirements.yml`. Here is an example of `requirements.yml` file:

```yaml
collections:
  - name: kewlfft.aur
```

### Install the `kewlfft.aur` collection from the AUR

The `kewlfft.aur` collection is also available in the AUR as the [`ansible-collection-kewlfft-aur`](https://aur.archlinux.org/packages/ansible-collection-kewlfft-aur/) package.

### Install the `kewlfft.aur` collection locally for development

If you want to test changes to the source code, run the following commands from the root of this git repository to locally build and install the collection:

```shell
ansible-galaxy collection build --force
ansible-galaxy collection install --force "./kewlfft-aur-$(cat galaxy.yml | grep version: | awk '{print $2}').tar.gz"
```

### Install the `aur` module as a local custom module

Alternatively, you may manually install the `aur` module itself as a [local custom module](https://docs.ansible.com/ansible/latest/dev_guide/developing_locally.html) instead of installing the module through the `kewlfft.aur` Ansible collection. However, it is recommended to use `kewlfft.aur` collection unless you have a good reason not to. Here are the commands to install the `aur` module as a local custom module:

```shell
# Create the user custom module directory
mkdir ~/.ansible/plugins/modules

# Install the aur module into the user custom module directory
curl -o ~/.ansible/plugins/modules/aur.py https://raw.githubusercontent.com/kewlfft/ansible-aur/master/plugins/modules/aur.py
```

## kewlfft.aur.aur Module

Ansible module to use some Arch User Repository (AUR) helpers as well as makepkg.
The following helpers are supported and automatically selected, if present, in the order listed below:

- [yay](https://github.com/Jguer/yay)
- [paru](https://github.com/Morganamilo/paru)
- [pacaur](https://github.com/E5ten/pacaur)
- [trizen](https://github.com/trizen/trizen)
- [pikaur](https://github.com/actionless/pikaur)
- [aurman](https://github.com/polygamma/aurman) (discontinued)

*makepkg* will be used if no helper was found or if it is explicitly specified:

- [makepkg](https://wiki.archlinux.org/index.php/makepkg)

### Options

| Parameter      | Choices/**Default**                                          | Comments                                                                                                                                     |
| -------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| name           |                                                              | Name or list of names of the package(s) to install or upgrade.                                                                               |
| state          | **present**, latest                                          | Desired state of the package, 'present' skips operations if the package is already installed.                                                |
| upgrade        | yes, **no**                                                  | Whether or not to upgrade whole system.                                                                                                      |
| update_cache        | yes, **no**                                                  | Whether or not to refresh the packages cache |
| use            | **auto**, yay, paru, pacaur, trizen, pikaur, aurman, makepkg | The tool to use, 'auto' uses the first known helper found and makepkg as a fallback.                                                         |
| extra_args     | **null**                                                     | A list of additional arguments to pass directly to the tool. Cannot be used in 'auto' mode.                                                  |
| aur_only       | yes, **no**                                                  | Limit helper operation to the AUR.                                                                                                           |
| local_pkgbuild | Local directory with PKGBUILD, **null**                      | Only valid with makepkg or pikaur. Don't download the package from AUR. Build the package using a local PKGBUILD and the other build files.  |
| skip_pgp_check | yes, **no**                                                  | Only valid with makepkg. Skip PGP signatures verification of source file, useful when installing packages without GnuPG properly configured. |
| ignore_arch    | yes, **no**                                                  | Only valid with makepkg. Ignore a missing or incomplete arch field, useful when the PKGBUILD does not have the arch=('yourarch') field.      |

#### Note

* Either *name* or *upgrade* is required, both cannot be used together.
* In the *use*=*auto* mode, makepkg is used as a fallback if no known helper is found.

### Usage

#### Notes

* The scope of this module is installation and update from the AUR; for package removal or for updates from the repositories, it is recommended to use the official *pacman* module.
* The *--needed* parameter of the helper is systematically used, it means if a package is up-to-date, it is not built and reinstalled.

#### Create the "aur_builder" user

While Ansible expects to SSH as root, makepkg or AUR helpers do not allow executing operations as root, they fail with "you cannot perform this operation as root". It is therefore recommended to create a user, which is non-root but has no need for password with pacman in sudoers, let's call it *aur_builder*.

This user can be created in an Ansible task with the following actions:

```yaml
- name: Create the `aur_builder` user
  become: yes
  ansible.builtin.user:
    name: aur_builder
    create_home: yes
    group: wheel

- name: Allow the `aur_builder` user to run `sudo pacman` without a password
  become: yes
  ansible.builtin.lineinfile:
    path: /etc/sudoers.d/11-install-aur_builder
    line: 'aur_builder ALL=(ALL) NOPASSWD: /usr/bin/pacman'
    create: yes
    mode: 0644
    validate: 'visudo -cf %s'
```

#### Fully Qualified Collection Names (FQCNs)

In order to use an Ansible module that is distributed in a collection, you must use its FQCN. This corresponds to "the full definition of a module, plugin, or role hosted within a collection, in the form `namespace.collection.content_name`" ([Source](https://github.com/ansible-collections/overview#terminology)). In this case, the `aur` module resides in the `aur` collection which is under the `kewlfft` namespace, so its FQCN is `kewlfft.aur.aur`.

Please note that this does not apply if you installed the `aur` module as a local custom module. Due to the nature of local custom modules, you can simply use the module's short name: `aur`.

#### Examples

Use it in a task, as in the following examples:

```yaml
# This task uses the module's short name instead of its FQCN (Fully Qualified Collection Name).
# Use the short name if the module was installed as a local custom module.
# Otherwise, if it was installed through the `kewlfft.aur` collection, this task will fail.
- name: Install trizen using makepkg if it isn't installed already
  aur:
    name: trizen
    use: makepkg
    state: present
  become: yes
  become_user: aur_builder

# This task uses the `aur` module's FQCN.
- name: Install trizen using makepkg if it isn't installed already
  kewlfft.aur.aur:
    name: trizen
    use: makepkg
    state: present
  become: yes
  become_user: aur_builder

- name: Install package_name_1 and package_name_2 using yay
  kewlfft.aur.aur:
    use: yay
    name:
      - package_name_1
      - package_name_2

# Note: Dependency resolution will still include repository packages.
- name: Upgrade the system using yay, only act on AUR packages.
  kewlfft.aur.aur:
    upgrade: yes
    use: yay
    aur_only: yes

# Skip if it is already installed
- name: Install gnome-shell-extension-caffeine-git using pikaur and a local PKGBUILD.
  kewlfft.aur.aur:
    name: gnome-shell-extension-caffeine-git
    use: pikaur
    local_pkgbuild: {{ role_path }}/files/gnome-shell-extension-caffeine-git
    state: present
  become: yes
  become_user: aur_builder
```
