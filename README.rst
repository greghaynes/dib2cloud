=========
dib2cloud
=========

Maintain a set of images in a cloud using diskimage-builder


Installation
------------

Make sure you have the system dependencies for diskimage-builder installed:

.. code:: bash

    sudo apt-get update || true
    sudo apt-get install -y --force-yes \
            debootstrap \
            inetutils-ping \
            lsb-release \
            kpartx \
            qemu-utils \
            uuid-runtime || \
        sudo yum -y install \
            debootstrap \
            kpartx \
            qemu-img || \
        sudo emerge \
            app-emulation/qemu \
            dev-python/pyyaml \
            sys-block/parted \
            sys-fs/multipath-tools


Install dib2cloud from git

.. code:: bash

    git clone https://github.com/greghaynes/dib2cloud
    sudo pip install -U ./dib2cloud


Usage
-----

Create an ubuntu image

.. code:: bash

    dib2cloud build dib2cloud-ubuntu-debootstrap

Vew builds

.. code:: bash

    dib2cloud list-builds

Delete a build

.. code:: bash

    dib2cloud delete-build <id>

Upload an image (cloud-name is a cloud defined in os-client-config).

.. code:: bash

    dib2cloud upload <id> <cloud-name>

View uploads

.. code:: bash

    dib2cloud list-uploads


Configuration
-------------

By default configuration is specified in `/etc/dib2cloud.yaml`. It can also
be specified on the command line using the `--config-path` argument.

Images are specified in the configuration and several images begining
with `dib2cloud-` are defined by default. A configuration is not required
to use dib2cloud, but it is useful for building custom images.

Example configuration:

.. code:: yaml

    diskimages:
      - name: myimage
        elements:
          - fedora-minimal
          - vm
