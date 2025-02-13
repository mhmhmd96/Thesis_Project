
sudo ovsdb-server --remote=punix:/usr/local/var/run/openvswitch/db.sock \
    --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
    --private-key=db:Open_vSwitch,SSL,private_key \
    --certificate=db:Open_vSwitch,SSL,certificate \
    --bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert \
    --pidfile --detach --log-file
   
sudo ovs-vsctl --no-wait init
sudo ovs-vswitchd --pidfile --detach --log-file
#sudo ovs-vsctl set controller br0 connection-mode=out-of-band

python3 limit.py
