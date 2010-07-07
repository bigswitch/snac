.. _principals:

Principal Management
=====================

A primary function of the Policy Manager application is to manage
networks principals.  A *network principal* is any named entity on the
network (:ref:`Switches <switch_management>` and :ref:`Locations
<location_management>`) and network clients (:ref:`Hosts
<host_management>` and :ref:`Users <user_management>`).

The policy manager use principals names (as well as conventional
identifiers such as IP and MAC addresses) to enforce network policy 
and provide network visibility.

The policy manager supports the following principal types:

* :ref:`Switch <switch_management>`\ : A network switch.
* :ref:`Location <location_management>`\ : A physical port on a switch.  
  Location names are unique throughout the network.
* :ref:`Host <host_management>`\ : An addressable device that sends and 
  receives network traffic.  Hosts may have multiple interfaces and addresses.
* :ref:`User <user_management>`\ : An account used to identify an 
  authenticated person on the network.

Information associated with principals (such as authorization
credentials) are stored in *directories*.   The Policy Manager can be
configured to work with standard authentication stores such as LDAP
or Active Directory.  It also has an internal directory called
"Built-in".

It is possible to configure the Policy Manager to use multiple
directories.  For example, *user* accounts may be both handled by an
external authentication store (e.g., LDAP) as well as the "Built-in"
directory.  In such cases, it is necessary to distinguish which
directory a name is from.  This is done by prepending the directory name 
to the principal name.  For example, if both the LDAP directory and the
"Built-in" directory have the user *John*, they would be represented as
*LDAP_directory_name;John* and *Built-in;John*, respectively.  


.. _switch_management:

Managing Switches
-----------------

Viewing Registered and Discovered Switches
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In the *Monitors* tab, click on the *Switches* link on the sidebar
to navigate to the switch overview page.  The switch overview page
displays all registered and discovered switches on the network.


Registering Switches
^^^^^^^^^^^^^^^^^^^^
Switches configured with the Policy Manager's IP address should automatically
attempt to connect to the Policy Manager.  In order for the switch to join
the network, it must be registered.

To register a new switch, follow these steps:

#. In the *Monitors* tab, click on the *Switches* link the sidebar.
#. If configured correctly, the new switch should appear in the list of
   switches as "unregistered".

   .. image:: unreg_switch.png

#. Select the switch by clicking on it (the switch line should be highlighted).
#. Click the *Register Switch* button.
#. In the resulting pop-up, select the "Built-in" directory and
   enter a name for the switch.

   .. image:: reg_switch.png

#. The switch should now be allowed on the network and managed by the
   Policy Manager.

Resetting a Switch
^^^^^^^^^^^^^^^^^^
To reboot a switch, click the **Reset Switch** button on the
switch details page.

.. _host_management:

Hosts
------
Hosts identify network devices that send and receive network traffic.  
Policy for host principals is enforced regardless of the host's location 
or network addresses.

Viewing Registered and Discovered Hosts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In the *Monitors* tab, click on the *Hosts* link on the sidebar
to navigate to the Hosts overview page.  This page displays all
registered and discovered hosts on the network.

Registering Hosts
^^^^^^^^^^^^^^^^^

Registering a Discovered Host
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If an unregistered host is active on the network, the host will appear in 
the Hosts overview page as a member of the "discovered" directory.  The
discovered host name will be "host <MAC address>" 
if the host is connected to the switch L2.  Alternately, the
discovered hostname will be "host <IP address>" if there is a router 
or other L3 device between the host and the switch. 

To register a host that has been discovered, follow these steps:

#. Click on the host name from the Hosts overview page to navigate to the host
   details page.

#. Change the directory name from "discovered" to "Built-in".  To edit
   the directory name, click on the edit indicator that appears when hovering
   over the name.

#. The host is now registered with the static bindings that were
   detected when the host was seen.  To add or modify the host's static
   bindings, follow the steps outlined below. 

Registering a New Host
~~~~~~~~~~~~~~~~~~~~~~
To manually register a new host, follow these steps:

#. From the Hosts overview page, click the *Add Host* button.
#. Select the "Built-in" directory, and enter a name for the host.
#. The host is now registered, however no bindings are set.  To add
   static bindings to the host, follow the steps below. 

Updating Host Bindings
^^^^^^^^^^^^^^^^^^^^^^
Hosts have *static* and *active* binding attributes.  Active bindings 
represent the address(es) and location(s) the host is currently using on the
network.  Static bindings tell NOX how to identify name a host when it becomes 
active on the network.  If a host on the network uses a MAC and IP address
that does not match a static binding, that host will be placed in a special
"discovered" directory that contains all unregistered principals.  

It is important to note that hosts are identified by addresses available
to the Policy Manager.  If they reach a switch controlled by the Policy
Manager from behind an L3 router, then they must have at least one IP
address to be identified.  Hosts that connect directly to Policy Manager
controlled switches only need to have their MAC addresses registered.  

To modify static bindings for a host, follow these steps:

#. Click on the host name from the Hosts overview page to navigate to the host
   details page.
#. Locate the Static Bindings section of the host details page to view
   all static bindings currently registered for the host.
#. A new static binding may be added by clicking the *Add New Binding*
   button.
   
   #. To set a MAC or IP address for the new binding, double click on
      the associated field.

#. Static bindings may be removed by selecting the binding to remove (it
   will be highlighted when selected) and clicking the *Delete
   Selected* button.

Managing Host Groups
^^^^^^^^^^^^^^^^^^^^

Host groups can be accessed in the *Monitors* section under the *Groups*
and then *Host Groups* links.  The default system policy uses a number
of host groups which are created at system install time.  These include a
number of standard host types and roles.  

During initial configuration, the administrator should add relevant
servers to the appropriate groups.  The type of host expected in each
group is described below:

#. **DHCP Servers**  Networks which use DHCP for allocating IP addresses should add all DHCP servers to this group.  If the Policy Manager itself is being used for DHCP it is not necessary to add it to this group.
#. **DNS Servers** All DNS servers. 
#. **Controllers** All Policy Manager servers should be registered in this group. 
#. **LDAP Servers** Hosts providing directory service needed for authentication (e.g., LDAP or AD servers) must be added to this group. 
#. **User Auth Portals** By default the captive web portal is run on the controller in which case there is no need to add hosts to this group.  However, if a remote captive portal is used it must be added.
#. **Unrestricted Servers** Any additional host that requires unrestricted connectivity either for principal authentication or otherwise should be added to this group.  

Adding and removing hosts from groups can be done by clicking on the
group link and using the *Add Member* and *Remove Member* buttons.


.. _user_management:

Users
------

User principals identify a user account on the network.  When a user principal
authenticates to the network from a host, network access policies for the host
are updated to reflect any policies defined for the user.

Viewing Registered and Active Users
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In the *Monitors* tab, click on the *Users* link on the sidebar
to navigate to the user overview page.  The user overview page displays all
registered users in the "Built-in" directory, and all active users in any
directory.

Registering Users
^^^^^^^^^^^^^^^^^
User principals are supported in both the "Built-in" directory and in
external directories through LDAP.  (For instructions on configuring an
external LDAP directory, see :ref:`conf_ldap`.)  To add a new user in
the "Built-in" directory, follow these steps:

#. In the *Monitors* tab, click on the *Users* link on the sidebar.
#. Click the *Add User* button.
#. Select the "Built-in" directory, enter a username, and click *Add*.
#. The user will be created and the user details page will automatically
   be displayed.
#. User attributes may be set by clicking on the edit icon that appears
   when hovering over the associated field.
#. To enable a password on the user, follow the instructions for
   updating user passwords below.

Updating User Passwords
^^^^^^^^^^^^^^^^^^^^^^^
To update passwords on user principals, follow the steps below:

#. In the *Monitors* tab, click on the *Users* link on the sidebar.
#. Navigate to the User Details page by clicking on the username.
#. Click the *Change Password* button.
#. To set or change the password, enter the new password twice and click
   *Change Password*.
#. To disable password access for the account, click the *Clear
   Password* button.


.. _location_management:

Managing Locations
------------------

Locations identify a port on a switch where one or more hosts 
can connect.  Locations are part of a switch and may not be added or
removed.

By default, locations are named using the format <switch name>:<port name>.
Locations may be renamed from the Location Details page by following the
steps below:

#. In the *Monitors* tab, click on the *Locations* link on the
   sidebar.
#. Navigate to the location details page by clicking on the location
   name.
#. Click the edit icon that appears when hovering over the location name
   attribute to active the edit dialog.
#. Enter the new name and press enter.

