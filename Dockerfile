FROM archlinux:latest

# Install dependencies.
ARG mirror_country=US
RUN curl "https://www.archlinux.org/mirrorlist/?country=$mirror_country&protocol=https&ip_version=4&use_mirror_status=on" \
    | sed --expression "s/^#//" \
    > /etc/pacman.d/mirrorlist \
 && pacman -Syyu --noconfirm --needed \
 && pacman -S --noconfirm --needed \
      ansible \
      base-devel \
      sudo

# Create aur_builder user.
RUN useradd --create-home --group=wheel aur_builder \
 && echo 'aur_builder ALL=(ALL) NOPASSWD: /usr/bin/pacman' \
    > /etc/sudoers.d/11-install-aur_builder \
 && visudo -c -f /etc/sudoers.d/11-install-aur_builder \
 && chmod 0644 /etc/sudoers.d/11-install-aur_builder

# Run the playbook.
WORKDIR /opt
COPY library/ ./library/
COPY integration-test.yml ./
RUN ansible-playbook --module-path library integration-test.yml
