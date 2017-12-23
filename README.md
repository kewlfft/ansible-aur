# Ansible AUR package manager
Ansible module to use some AUR helpers. The following helpers are supported:
- [pacaur](https://github.com/rmarquis/pacaur) (default)
- [trizen](https://github.com/trizen/trizen)
- [yaourt](https://github.com/archlinuxfr/yaourt)
- [yay](https://github.com/Jguer/yay)

## Options
|parameter|required |default |choices                     |comments|
|---      |---      |---     |---                         |---|
|name     |no       |        |                            |Name or list of names of the package(s) to install or upgrade.|
|upgrade  |no       |no      |yes, no                     |Whether or not to upgrade whole system.|
|helper   |no       |pacaur  |pacaur, trizen, yaourt, yay |Helper to use.|

### Note
Either *name* or *upgrade* is required, both can not be used together.

## Installing
1. Add as a submodule in your playbook:
  ```
  mkdir --parents library/external_modules
  git submodule add git://github.com/kewlfft/ansible-aur.git library/external_modules/ansible-aur
  ```

2. Link the script to the base of `library/`:
  ```
  ln --symbolic external_modules/ansible-aur/aur.py library/aur
  ```

## Usage
### Warning
* It is recommended to use the official *pacman* module for removals or for upgrades with the repositories, this module aims to cover the AUR,
* Searches are limited to the AUR using the *--aur* parameter except for *yay* and *yaourt* which do not support it and systematically search the repositories,
* A package is reinstalled only if an update is available using the *--needed* parameter except for *yay* which do not support it and systematically reinstalls,

### Examples
Use it in a task, as in the following examples:
  ```
  # Install (using pacaur)
  - aur: name=package_name
    become: yes
    become_user: user_that_has_nopasswd_in_sudoers_for_pacman_use

  # Install (using trizen)
  - aur:
      helper: trizen
      name:
        - package_name_1
        - package_name_2 
    [...]

  # Upgrade (using pacaur)
  - aur: upgrade=yes
    [...]
  ```
