# Ansible AUR package manager
Ansible module to use some AUR helpers. The following helpers are supported and automatically selected according to the below order:
- [pacaur](https://github.com/rmarquis/pacaur)
- [trizen](https://github.com/trizen/trizen)
- [yaourt](https://github.com/archlinuxfr/yaourt)
- [yay](https://github.com/Jguer/yay)
- internal helper

## Options
|parameter      |required |default |choices                                      |comments|
|---            |---      |---     |---                                          |---|
|name           |no       |        |                                             |Name or list of names of the package(s) to install or upgrade.|
|upgrade        |no       |no      |yes, no                                      |Whether or not to upgrade whole system.|
|use            |no       |auto    |auto, pacaur, trizen, yaourt, yay, internal  |The helper to use, 'auto' uses the first known helper found, 'internal' uses the internal helper.|
|skip_installed |no       |no      |yes, no                                      |Skip operations if the package is present.|

### Note
* Either *name* or *upgrade* is required, both cannot be used together.
* *skip_installed* cannot be used with *upgrade*.
* In the *use* *auto* mode, the internal mode is used as a fallback if no known helper is found

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
### Warning
* It is recommended to use the official *pacman* module for removal or for system upgrade with the repositories, this module aims to cover the AUR.
* Searches are limited to the AUR, using the *--aur* parameter, except for *yay* and *yaourt* which do not support it and systematically search the repositories.
* A package is reinstalled only if an update is available, using the *--needed* parameter, except for *yay* which does not support it and systematically reinstalls.

### Examples
Use it in a task, as in the following examples:
```
# Install trizen using the internal helper, skip if trizen is already installed
- aur: name=trizen use=internal skip_installed=true
  become: yes
  become_user: user_that_has_nopasswd_in_sudoers_for_pacman_use

# Install package_name using the first known helper found
- aur: name=package_name
  become: yes
  become_user: user_that_has_nopasswd_in_sudoers_for_pacman_use

# Install package_name_1 and package_name_2 using trizen
- aur:
    use: trizen
    name:
      - package_name_1
      - package_name_2 
  [...]

# Upgrade - using pacaur
- aur: upgrade=yes use=pacaur
  [...]
```
