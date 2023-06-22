In this document my solutions for the tasks from SOC.docx will be presented.

--- General assumptions ---

For this assignment, I assumed that there are three servers running Ubuntu  Ubuntu 22.04.2 LTS. One of this servers is Splunk server set up according to the requirements from tasks, second server is  fresh minimal
headless instalation of Ubuntu 22.04.2 LTS (no splunk no prerequisites, just pure system), finally third server will be external ansible server (also running Ubuntu) with ansible installed and synced with 
Splunk_solutios repository. In this document will be described:

- automatic deployment of Splunk instance with all prerequisites
- configuring splunk server(all in one deployment) according to the requirements from Tasks 1 & 2
- automation of Splunk configuration management as well as the necessary components of the operating system.


1. Splunk deployment Automation

a. Ansible user configuration(simone)

First of all SSH key for ansible needs to be created. It can be done by issuing this command on ansible server:

ssh-keygen -t ed25519 -C "ansible"

Then public key need to be added on server(s) that we want to manage with ansible:

ssh-copy-id -i ~/.ssh/ansible.pub <server(s)_ip>

Next important step is to create ansible user on remote server(s). Ansible can be used to do that with playbook ansible_setup.yml from Splunk_solutions repo. This is the only ansible command that will need sudo password
from remote server user. This command will create simone user for managing ansible on remote server:

ansible-playbook ansible_setup.yml --ask-become-pass

b. Installing splunk and Linux prerequisites on remote server(s). To install Splunk and Linux prerequisites install.yml  playbook will be used. This is slightly modified version of playbook created and shared on https://github.com/johnmcgovern/ansible-splunk-base . Unfortunately Splunk version 8.2.9 on Ubuntu 22.04.2 has problem related with Linux cgroups (https://community.splunk.com/t5/Installation/Why-is-Systemd-broken-on-new-install/td-p/482881), to fix that I changed line 215 in core-instalation playbook. To install splunk with all Linux prerequisites issue that command on ansible server:

![Script execution](https://github.com/Filip-Kuczak/Splunk_solutions/assets/77390537/77140973-bb64-49cb-a4ff-2f4125f6216c)

![blocklist_monitor 2 ](https://github.com/Filip-Kuczak/Splunk_solutions/assets/77390537/7bd69b5f-897b-4dab-8923-6f8618e33917)



ansible-playbook install.yml -u simone         (optionally line 14 in /Splunk_solutions/group_vars/all could be uncommented, after that -u flag will not be needed in 
further executions)

after that splunk_version: 8.2.9 will be installed and user splunk will be created. Splunk will be managed by systemd

2. Tasks:

General approach(proposed as a solutions) on how to maintain and control splunk configuration is to use apps. For sake of this tasks I decided to create seprate app which will reflect each aspect mentioned in SOC.docx objectives. Code for apps is stored in Splunk_solutions/roles/splunk_all_in_one/files/apps

a. TCP/UDP inputs - to represent this Quadcode_syslod_inputs app was created. Iside there are simle tcp input in inputs.conf and index syslog_data. Data source is set to default splunk syslog.

b. (TASK 2)For REST API inputs Quadcode_blocklist_monitor app was created. Splunk will fire blocklist.py scripy every 3600 (1 hour) . For this input custom sourcetype was creted (blocklist). As collected data consisits only of ip addresses I created realy simple props.conf to create line breaking and transforms.conf to demostrated potential regex usage. In props simple eval was used to show how to create calculated fields. Below is the screenshot of indexed data from scripted input. 

As for the script itself it is realy simple python code that checks current time and substracts 3600 from it. Then epoch value of current time - 3600 seconds is provide as argument for time= parameter in blocklit api. 

c. Quadcode_monitoring app contains simple schedule search (in savedsearches.conf) the querries blocklist index for any occurences of IPv6. It is scheduled to run at every 45th minute.

d. Quadcode_local_inputs querries local file error.log genereated by apache2 (of course there is TA great for Apache :) for the sake of local logs ingestion. According to task description from SOC.docx previous engineer did not left decent documentation but we know the names of the services and we can check what files are monitored. These two facts connected together should give us clear picture on what services should be started on potential replicated server. 

3. App management and server migration strategy. 

When splunk configurations are managed via apps there is big possibility to be very flexible with replicating configurations. Strategy to maintain and store configs is as follows:


a. Apps are stored in git within ansible splunk_all_in_one role 
b. Naming convention is that names always start Quadcode_
c. Configs are modified witihin ansible role and then deployed with ansible playbook splunk_all_in_one.yml
d. Users keeps config in sync with git repo. 
e. If for some reasons any changes needs to be done within $SPLUNK_HOME/etc/system/local then it should be stored in system_local directory witihn ansible role and managed via ansible

APP MANAGEMENT

The system for managing aps is realy simple. Ansible will copy all apps that from splunk_all_in_one role /files/apps and /files/system_local to $SPLUNK_HOME/etc/apps and $SPLUNK_HOME/etc/system/local by that the old version will be replaced by most recent version from git and splunk config will be always in sync with git. Ansible role will also take care of poprer user, group and files/directories permissions. The potential disadvantage of this solution is the fact that we don't have control of deleted appps. For example if app is deleted from git/ansible, then the last version will remain on splunk server. The solution might be to delete it manually or add additional step to ansible role which will delete all apps starting from Quadcode_ and then put the newest versions (it won't be dangerous because splunk will start using new configurations only after restart). Of course the second soultion is less efficinet and should be discussed before potential implementation.

MIGRATION 

First of all, make sure that all applications are managed by GIT, are up to date, managed by ansbile and follow the naming conventions(also potential system/local files should be checked). If not, it should be corrected before proceeding to the next steps. In case of Splunk_solutions repo everything is set well and up to date. Next step will be to make sure that all systemd services are added to splunk_all_in_one role. In ansible splunk_all_in_one role:  there is always check if server repositories are up to date (if not ansible will update it), and if important services are running, if not ansible will update them (in case of this task it is just apache2 but there is potential for more services).   


As in the task 1 from SOC.docx it was mentioned that splunk ingests data via TCP/UDP then using DNS name instead of just ip address would be a good solution and will prevent from any potential configuration changes the would have to be done on devices sending data to Splunk. It will also prevent from any downtime during migration because the migrated server will be able to be fully checked before making changes in DNS records. 

Another network related issue worth considering is connectivity between devices sending logs and new splunk server (there might be need to create some rules on firewall). 

If data  send via TCP/UDP is encrypted the SSL certs also should be copied.

If external storage is used, the connectivity between new server and storage should be checked.


Using this method is relatively fast and safe to migrate splunk all_in_one server to another machine. After installing splunk and prerequisites Engineer should log in and check if splunk works as expected, then if all requirements mentioned above are met, the dnsnaeme/ip address of new server should be added in splunk server1 stanza in inventory file from Splunk_solutions repo. After cheking if everything is working fine, dns name should be switched to the new server. The potential risk is relatively small because we can have two servers running simultaneously until we are sure tha everything works as it should.


