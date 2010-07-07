.. _switch-ui:

Switch User Interface
=====================

Network switches supplied by Nicira have a user interface that may be
used to monitor network behavior and configure certain settings.
The user interface to these switches consists of a 16-column, 2-row
LCD text display and four buttons, labeled ``▲``, ``▼``, ``ESC``, and
``ENTER``, respectively.  For easier input, a keyboard may be plugged
in to one of the switch's USB ports.

Information Screen
------------------

In ordinary operation, the switch user interface automatically cycles
through a series of screens that display information of general
interest, such as the switch's host name, the number of flows
currently active on the switch, and the amount of traffic passing
through the switch.  The ``▲`` and ``▼`` buttons may be used to
manually select a particular screen.  Pressing ``ENTER`` stops the
automatic cycling behavior, freezing the user interface at the current
screen for 60 seconds.

Switch Main Menu
----------------

From any of the monitoring screens, pressing ``ESC`` brings up a menu
with one item per line.  The currently selected menu item is indicated
by ``▶`` at the start of a line.  In the menu, the ``▲`` and ``▼``
buttons may be used to select an item, ``ENTER`` selects the current
item, and ``ESC`` exits the menu without making a selection. 

The menu contains the following items:

Exit
    Exits the menu without taking any action.

Show Version
    Displays the version number of the switch software.

Configure
    Allows the user to change basic switch settings (see below).

After interaction with the menu is complete, the switch returns to the
information screen.

Switch Configuration
--------------------

Basic switch settings may be configured through the switch UI by
selecting ``Configure`` from the main menu.  This brings up a
secondary menu that displays a number of settings, one per screen:

Exit
    This exits the configuration menu (see below).

Mode
    May be set to ``Discovery`` or ``In-Band``.  Select ``Discovery``
    only if an OpenFlow switch-aware DHCP server is configured in your
    network.

    When ``Discovery`` is selected, the remaining settings are
    disabled, because discovery will automatically select the correct
    values.

Switch IP
    The IP address to be used by the switch (e.g. ``192.168.0.2``).

    Changing the switch IP address also changes the switch netmask and
    gateway (see below) to their most common values.

Switch Netmask
    The netmask of the switch's local IP network
    (e.g. ``255.255.255.0``).

Switch Gateway
    The IP address of the gateway between the local IP network and
    external networks (e.g. ``192.168.0.1``).

Controller
    NOX's location, in the form TYPE:IP[:PORT], where TYPE is one of
    the literal strings ``tcp`` or ``ssl``, IP is an IP address, and
    the optional PORT is a TCP port number between 1 and 65535.

To change a setting, select it with ``▲`` and ``▼`` and push
``ENTER``.  The ``▲`` and ``▼`` buttons may then be used to cycle
individual characters of a setting through the valid values, ``ENTER``
to accept the current selection, and ``ESC`` to back up.  If a USB
keyboard is plugged in, then the new setting may be typed directly.
After the setting's value is complete, push ``ENTER`` when ``↵`` is
displayed to accept the new value.  To cancel changes, push ``ESC``
repeatedly.

When configuration is complete, push ``ESC`` from the menu of
settings (or select ``Exit`` and push ``ENTER``).  At the ``Save
Changes?`` prompt, select ``Yes`` or ``No`` with ``▲`` and ``▼`` (or
by pushing ``Y`` or ``N`` on an attached USB keyboard) and push
``ENTER``.  If ``Yes`` is selected, the changes take effect
immediately.
