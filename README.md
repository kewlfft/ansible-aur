# Ansible AUR helper
Ansible module to use some Arch User Repository (AUR) helpers as well as a simple internal implementation as a fallback. The following helpers are supported and automatically selected in the order they are listed:
- [aurman](https://github.com/polygamma/aurman)
- [pacaur](https://github.com/rmarquis/pacaur)
- [trizen](https://github.com/trizen/trizen)
- [pikaur](https://github.com/actionless/pikaur)
- [yaourt](https://github.com/archlinuxfr/yaourt)
- [yay](https://github.com/Jguer/yay)
- internal helper

## Options
|parameter      |required |default |choices                                                      |comments|
|---            |---      |---     |---                                                          |---|
|name           |no       |        |                                                             |Name or list of names of the package(s) to install or upgrade.|
|upgrade        |no       |no      |yes, no                                                      |Whether or not to upgrade whole system.|
|use            |no       |auto    |auto, aurman, pacaur, trizen, pikaur, yaourt, yay, internal  |The helper to use, 'auto' uses the first known helper found, 'internal' uses the internal helper.|
|skip_installed |no       |no      |yes, no                                                      |Skip operations if the package is present.|

### Note
* Either *name* or *upgrade* is required, both cannot be used together.
* *skip_installed* cannot be used with *upgrade*.
* In the *use*=*auto* mode, the internal helper is used as a fallback if no known helper is found.

## Installing
1. Clone the *ansibe-aur* repository in your playbook custom-module directory:
```
mkdir --parents library
cd library
git clone git@github.com:kewlfft/ansible-aur.git
```

2. Link the script to `library/aur`:
```
ln --symbolic ansible-aur/aur.py aur
```

## Usage
### Note
* This module aims to cover the AUR, for package removal or system upgrade with the repositories, it is recommended to use the official *pacman* module,
* A package is reinstalled only if an update is available, using the *--needed* parameter, except for *yay* which does not support it and systematically reinstalls.

### Examples
Use it in a task, as in the following examples:
```
# Install trizen using the internal helper, skip if trizen is already installed
- aur: name=trizen use=internal skip_installed=true
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
While Ansible expects to SSH as root, AUR helpers do not allow executing operations as root, they all fail with "you cannot perform this operation as root". It is therefore recommended to create a user, that we will call for example *aur_builder*, that has no need for password with pacman in sudoers.
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