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

To create an ubuntu image

.. code:: bash

    dib2cloud build ubuntu-debootstrap

To view builds

.. code:: bash

    dib2cloud list-builds

To delete a build

.. code:: bash

    dib2cloud  delete-build <id>
