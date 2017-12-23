*ansible-aur* is an Ansible module to use some AUR helpers.

The following AUR helpers are supported:

- pacaur (default)
- trizen
- yaourt
- yay

> Notes:
> * It is recommended to use the official *pacman* module for removals or for upgrades with the repositories, this module focuses on the AUR,
> * Searches are limited to the AUR using the *--aur* parameter except for *yay* and *yaourt* which do not support it and also search the repositories,
> * A package is reinstalled only if an update is available using the *--needed* parameter except for *yay* which do not support it and reinstalls systematically,

## Options
|parameter|required |default |choices                     |comments|
|---      |---      |---     |---                         |---|
|name     |no       |        |                            |Name of the package to install or upgrade.|
|upgrade  |no       |no      |yes, no                     |Whether or not to upgrade whole system.|
|helper   |no       |pacaur  |pacaur, trizen, yaourt, yay |Helper to use.|

> Note: Either *name* or *upgrade* is required, both can not be used together, this is prevented to allow a meaningful *changed* output.

## Usage
1. Add as a submodule in your playbook:
   ```
   mkdir -p library/external_modules
   git submodule add git://github.com/kewlfft/ansible-aur.git library/external_modules/ansible-aur
   ```

2. Link the binary to the base of `library/`:
   ```
   ln -s external_modules/ansible-aur/aur library/aur
   ```

3. Use it in a task, as in the following examples:
   ```
   # Install (using pacaur)
   - aur: name=package_name
     become: yes
     become_user: user_that_has_nopasswd_in_sudoers_for_pacman_use

   # Install (using trizen)
   - aur: name=package_name helper=trizen
     [...]

   # Upgrade (using pacaur)
   - aur: upgrade=yes
     [...]
   ```
