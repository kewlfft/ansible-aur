# Ansible AUR helper
Ansible module to use some Arch User Repository (AUR) helpers as well as makepkg.

The following helpers are supported and automatically selected, if present, in the order listed below:
- [yay](https://github.com/Jguer/yay)
- [aurman](https://github.com/polygamma/aurman)
- [pacaur](https://github.com/rmarquis/pacaur)
- [trizen](https://github.com/trizen/trizen)
- [pikaur](https://github.com/actionless/pikaur)

*makepkg* will be used if no helper was found or if it is explicitly specified:
- [makepkg](https://wiki.archlinux.org/index.php/makepkg)

## Options
|parameter      |required |default |choices                                            |comments|
|---            |---      |---     |---                                                |---|
|name           |no       |        |                                                   |Name or list of names of the package(s) to install or upgrade.|
|upgrade        |no       |no      |yes, no                                            |Whether or not to upgrade whole system.|
|use            |no       |auto    |auto, yay, aurman, pacaur, trizen, pikaur, makepkg |The helper to use, 'auto' uses the first known helper found and makepkg as a fallback.|
|skip_installed |no       |no      |yes, no                                            |Skip operations if the package is present.|
|skip_pgp_check |no       |no      |yes, no                                            |Skip verification of PGP signatures. This is useful when installing packages on a host without GnuPG (properly) configured. Only valid with makepkg.|
|aur_only       |no       |no      |yes, no                                            |Limit operation to the AUR. Compatible with yay, aurman, pacaur and trizen.|

### Note
* Either *name* or *upgrade* is required, both cannot be used together.
* *skip_installed* cannot be used with *upgrade*.
* In the *use*=*auto* mode, makepkg is used as a fallback if no known helper is found.

## Installing
### AUR package
The [ansible-aur-git](https://aur.archlinux.org/packages/ansible-aur-git) package is available in the AUR.
Note the module is installed in `/usr/share/ansible/plugins/modules` which is one of the default module library paths.

### Manual installation
Just clone the *ansible-aur* repository into your user custom-module directory:
```
git clone https://github.com/kewlfft/ansible-aur.git ~/.ansible/plugins/modules/aur
```

## Usage
### Notes
* This module aims to cover the AUR; for package removal or system upgrade with the repositories, it is recommended to use the official *pacman* module.
* The *--needed* parameter of the helper is systematically used, it means if a package is up to date, it is not built and reinstalled.

### Examples
Use it in a task, as in the following examples:
```
# Install trizen using makepkg, skip if trizen is already installed
- aur: name=trizen use=makepkg skip_installed=true
  become: yes
  become_user: aur_builder

# Install package_name using the first known helper found
- aur: name=package_name
  ...

# Install package_name_1 and package_name_2 using trizen
- aur:
    use: trizen
    name:
      - package_name_1
      - package_name_2
  ...

# Upgrade - using pacaur
- aur: upgrade=yes use=pacaur
  ...
```

### Create the "aur_builder" user
While Ansible expects to SSH as root, AUR helpers do not allow executing operations as root, they all fail with "you cannot perform this operation as root". It is therefore recommended to create a user, let's call it *aur_builder*, that has no need for password with pacman in sudoers.
This can be done in Ansible with the following actions:
```
- user:
    name: aur_builder
    group: wheel
- lineinfile:
    path: /etc/sudoers.d/11-install-aur_builder
    line: 'aur_builder ALL=(ALL) NOPASSWD: /usr/bin/pacman'
    create: yes
    validate: 'visudo -cf %s'
```
